# -*- coding: utf-8 -*-
"""
知识库问题检测引擎

支持两种检测模式：
1. 规则检测（rule-based）：基于正则表达式、文本相似度、启发式规则
2. LLM 检测（llm-based）：调用 LLM API 进行语义分析，支持 mock 模式

两种模式可组合使用，规则检测快速筛出明确问题，LLM 检测补充语义层面的问题。
"""

import re
import json
import hashlib
from difflib import SequenceMatcher
from collections import defaultdict
from typing import List, Dict, Any, Optional

from .problem_types import ProblemType, SEVERITY_WEIGHT


# ============================================================
# 工具函数
# ============================================================

def text_similarity(text1: str, text2: str) -> float:
    """计算两段文本的相似度（0-1）"""
    if not text1 or not text2:
        return 0.0
    # 去除空白后比较
    t1 = re.sub(r'\s+', '', text1)
    t2 = re.sub(r'\s+', '', text2)
    if not t1 or not t2:
        return 0.0
    return SequenceMatcher(None, t1, t2).ratio()


def tokenize(text: str) -> List[str]:
    """简易中文分词（按字符 + 标点分割）"""
    # 仅保留中文、字母、数字
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]", "", text)
    # 按字符切分（适用于中文）
    return list(cleaned)


def extract_urls(text: str) -> List[str]:
    """提取文本中的URL"""
    url_pattern = r"https?://[^\s\uff0c\u3002\uff01\uff1f\u3001\uff1b\uff1a\uff09\u3011\u300b\]}]+"
    return re.findall(url_pattern, text)


def char_ngrams(text: str, n: int = 2) -> set:
    """生成字符n-gram集合"""
    cleaned = re.sub(r'\s+', '', text)
    if len(cleaned) < n:
        return {cleaned}
    return {cleaned[i:i+n] for i in range(len(cleaned) - n + 1)}


def jaccard_similarity(set1: set, set2: set) -> float:
    """Jaccard相似度"""
    if not set1 and not set2:
        return 0.0
    intersection = set1 & set2
    union = set1 | set2
    return len(intersection) / len(union) if union else 0.0


# ============================================================
# 业务规则检测器（基于 business_context.md）
# ============================================================

class BusinessRuleChecker:
    """
    根据当前业务规则摘要，检测知识库条目是否存在内容过时或矛盾。
    
    每条规则定义：
    - name: 规则名称
    - topic: 问题中需包含的主题词（至少匹配一个）
    - expected: 答案中应当体现的正确关键词（可选）
    - forbidden: 答案中若出现则视为与规则矛盾的关键词
    - severity: 严重等级
    """
    
    RULES = [
        {
            "name": "普通商品7天无理由退货",
            "topic": ["退货政策", "退货", "无理由"],
            "expected": ["7天", "七天"],
            "forbidden": ["30天无理由", "30天无理由退货", "15天无理由"],
            "severity": "critical",
        },
        {
            "name": "非质量问题退货运费买家承担",
            "topic": ["运费", "退货运费"],
            "expected": ["买家承担", "买家支付", "买家出"],
            "forbidden": ["所有退货.*运费.*商家承担", "运费.*商家承担", "退货运费.*商家承担", "不需要支付任何费用"],
            "severity": "critical",
        },
        {
            "name": "发货时间24小时内",
            "topic": ["发货", "多久能发货", "发货时间"],
            "expected": ["24小时"],
            "forbidden": ["48小时"],
            "severity": "critical",
        },
        {
            "name": "合作快递为中通、韵达、圆通",
            "topic": ["快递", "什么快递", "用的什么快递", "发什么快递"],
            "expected": ["中通", "韵达", "圆通", "系统自动分配"],
            "forbidden": ["顺丰"],
            "severity": "critical",
        },
        {
            "name": "到货时间一般3-5天",
            "topic": ["几天到", "多久到", "到货时间", "快递.*几天"],
            "expected": ["3-5天"],
            "forbidden": ["2-3天.*大部分", "2-3天到货"],
            "severity": "major",
        },
        {
            "name": "不支持货到付款",
            "topic": ["货到付款", "到付"],
            "expected": ["不支持", "不能"],
            "forbidden": ["支持货到付款", "可以货到付款"],
            "severity": "critical",
        },
        {
            "name": "仅支持电子发票，不支持纸质发票",
            "topic": ["发票", "开发票"],
            "expected": ["电子发票", "订单详情页申请"],
            "forbidden": ["纸质发票", "一起寄出纸质发票", "支持纸质"],
            "severity": "critical",
        },
        {
            "name": "银卡会员门槛为累计消费满2000元享95折",
            "topic": ["会员", "会员等级", "银卡"],
            "expected": ["2000元", "95折"],
            "forbidden": ["银卡.*1000元", "银卡.*9折"],
            "severity": "critical",
        },
        {
            "name": "金卡会员门槛为累计消费满8000元享9折",
            "topic": ["会员", "会员等级", "金卡"],
            "expected": ["8000元", "9折"],
            "forbidden": ["金卡.*5000元", "金卡.*85折"],
            "severity": "critical",
        },
        {
            "name": "当前优惠券为满200减20、满500减60",
            "topic": ["优惠券", "有什么券", "优惠活动"],
            "expected": ["满200减20", "满500减60"],
            "forbidden": ["满300减50", "满600减120"],
            "severity": "major",
        },
        {
            "name": "优惠券不叠加使用",
            "topic": ["优惠券.*叠加", "叠加使用"],
            "expected": ["不叠加", "不可叠加", "不能叠加"],
            "forbidden": ["可以叠加", "最多叠加"],
            "severity": "critical",
        },
        {
            "name": "在线客服9:00-22:00",
            "topic": ["在线客服", "客服.*时间", "客服.*工作"],
            "expected": ["9:00-22:00", "9点到22点"],
            "forbidden": ["7x24", "24小时", "全天候"],
            "severity": "critical",
        },
        {
            "name": "电话客服9:00-18:00",
            "topic": ["电话客服"],
            "expected": ["9:00-18:00", "9点到18点"],
            "forbidden": [],
            "severity": "major",
        },
        {
            "name": "邮件客服24小时内回复",
            "topic": ["邮件客服"],
            "expected": ["24小时"],
            "forbidden": [],
            "severity": "minor",
        },
    ]
    
    def __init__(self, context_text: str = ""):
        """
        Args:
            context_text: 业务规则摘要的原始文本（当前版本保留备用）
        """
        self.context_text = context_text
    
    def check(self, entries: List[Dict]) -> List[Dict]:
        """对所有条目执行业务规则冲突检测"""
        results = []
        for entry in entries:
            results.extend(self._check_entry(entry))
        return results
    
    def _check_entry(self, entry: Dict) -> List[Dict]:
        results = []
        question = entry.get("question", "")
        answer = entry.get("answer", "")
        text = question + " " + answer
        
        for rule in self.RULES:
            # 判断该条目是否涉及此规则主题
            if not self._topic_match(question, rule.get("topic", [])):
                continue
            
            # 若答案为空，跳过规则冲突检测（由 incomplete 处理）
            if not answer.strip():
                continue
            
            # 特殊规则：发货时间。若答案已声明"24小时内"，补充"大促可能延长至48小时"不算矛盾
            if rule["name"] == "发货时间24小时内":
                if re.search(r"24小时", answer) and re.search(r"48小时", answer):
                    continue
            
            # 特殊规则：到货时间。偏远地区7天是合理补充，不视为矛盾
            if rule["name"] == "到货时间一般3-5天":
                if re.search(r"3-5天", answer) and re.search(r"偏远.*7天", answer):
                    continue
            
            # 检测禁止内容
            for forbidden in rule.get("forbidden", []):
                if re.search(forbidden, answer):
                    results.append({
                        "problem_type": "outdated",
                        "issue_detail": f"业务规则冲突：{rule['name']}。当前答案「{answer[:40]}...」与业务规则矛盾（匹配模式：{forbidden}）",
                        "severity": rule.get("severity", "major"),
                    })
                    break  # 同一规则只报一次
        
        return results
    
    def _topic_match(self, question: str, topic_keywords: List[str]) -> bool:
        """判断问题是否涉及规则主题"""
        if not topic_keywords:
            return True
        for kw in topic_keywords:
            if re.search(kw, question):
                return True
        return False


# ============================================================
# 规则检测器
# ============================================================

class RuleDetector:
    """基于规则的问题检测器"""
    
    # 过时关键词（年份、已下线的功能名等）
    OUTDATED_PATTERNS = [
        (r'20[12][0-2]年', '引用了旧年份信息'),
        (r'20[12][0-2]年\d{1,2}月', '引用了旧时间信息'),
        (r'疫情.*?(暂停|延期|延迟|影响)', '引用疫情管控政策，可能已不适用'),
        (r'百度钱包', '百度钱包已更名为度小满支付'),
        (r'iPhone 1[0-3]\b', '引用了较旧的iPhone型号'),
    ]
    
    # 内部/测试地址模式
    INTERNAL_URL_PATTERNS = [
        r'https?://192\.168\.',
        r'https?://10\.',
        r'https?://localhost',
        r'https?://127\.0\.0\.1',
        r'https?://.*\.internal\.',
        r'https?://.*\.test\.',
        r'https?://.*\.local\b',
        r'https?://old-domain\.',
    ]
    
    # 模糊回答特征词
    VAGUE_PATTERNS = [
        r'^(挺|很|比较|还|蛮)好的?$',
        r'^快的话.{0,5}就到了?$',
        r'不一定',
        r'看.{0,4}情况',
        r'关注.{1,6}页面?$',
        r'咨询客服.{0,4}详情?$',
    ]
    
    # 格式问题模式
    FORMAT_PATTERNS = [
        (r'\n{3,}', '存在连续多个空行'),
        (r' {3,}', '存在连续多个空格'),
        (r'[^\n]{80,}', '单行过长，缺少换行'),
        (r'->.*?->.*?->.*?(?:取消|恢复)', '流程描述缺少换行分隔'),
    ]
    
    def __init__(self, business_context: str = ""):
        self.results = []
        self.biz_checker = BusinessRuleChecker(context_text=business_context)
    
    def detect_all(self, entries: List[Dict]) -> List[Dict]:
        """运行所有规则检测"""
        results = []
        
        # 单条目检测
        for entry in entries:
            entry_results = []
            entry_results.extend(self._check_outdated(entry))
            entry_results.extend(self._check_format(entry))
            entry_results.extend(self._check_vague(entry))
            entry_results.extend(self._check_dead_link(entry))
            entry_results.extend(self._check_qa_mismatch(entry))
            entry_results.extend(self._check_incomplete(entry))
            entry_results.extend(self.biz_checker.check([entry]))
            
            for r in entry_results:
                results.append({
                    "entry_id": entry["id"],
                    "question": entry["question"],
                    "category": entry["category"],
                    "problem_type": r["problem_type"],
                    "issue_detail": r["issue_detail"],
                    "severity": r["severity"],
                    "detection_method": "rule",
                })
        
        # 跨条目检测（需要两两比较）
        results.extend(self._check_duplicates(entries))
        results.extend(self._check_contradictions(entries))
        
        return results
    
    def _check_outdated(self, entry: Dict) -> List[Dict]:
        """检测内容过时"""
        results = []
        text = entry.get("answer", "") + " " + entry.get("question", "")
        
        for pattern, desc in self.OUTDATED_PATTERNS:
            if re.search(pattern, text):
                results.append({
                    "problem_type": "outdated",
                    "issue_detail": f"规则匹配：{desc}（匹配模式: {pattern}）",
                    "severity": "major",
                })
        
        return results
    
    def _check_format(self, entry: Dict) -> List[Dict]:
        """检测格式不规范"""
        results = []
        answer = entry.get("answer", "")
        
        for pattern, desc in self.FORMAT_PATTERNS:
            if re.search(pattern, answer):
                results.append({
                    "problem_type": "format_issue",
                    "issue_detail": f"规则匹配：{desc}",
                    "severity": "minor",
                })
        
        # 检查分隔符不一致
        separators = re.findall(r'[|/\\]', answer)
        if len(set(separators)) >= 3:
            results.append({
                "problem_type": "format_issue",
                "issue_detail": "规则匹配：使用了多种不同分隔符（/ | \\ 等），格式不一致",
                "severity": "minor",
            })
        
        # 检查括号样式不统一
        brackets = re.findall(r'[【】\[\]{}「」「」]', answer)
        bracket_types = set()
        for b in brackets:
            if b in '【】':
                bracket_types.add('【】')
            elif b in '[]':
                bracket_types.add('[]')
            elif b in '{}':
                bracket_types.add('{}')
            elif b in '「」':
                bracket_types.add('「」')
        if len(bracket_types) >= 3:
            results.append({
                "problem_type": "format_issue",
                "issue_detail": "规则匹配：括号样式不统一，混用了多种括号",
                "severity": "minor",
            })
        
        return results
    
    def _check_vague(self, entry: Dict) -> List[Dict]:
        """检测信息模糊"""
        results = []
        answer = entry.get("answer", "").strip()
        
        # 答案过短（更严格阈值）
        if len(answer) < 15 and len(entry.get("question", "")) > 10:
            results.append({
                "problem_type": "vague",
                "issue_detail": f"规则匹配：回答过短（仅{len(answer)}字），可能信息不充分",
                "severity": "major",
            })
        
        # 匹配模糊特征词
        for pattern in self.VAGUE_PATTERNS:
            if re.search(pattern, answer):
                results.append({
                    "problem_type": "vague",
                    "issue_detail": f"规则匹配：回答含有模糊表述（匹配: {pattern}）",
                    "severity": "major",
                })
                break
        
        return results
    
    def _check_dead_link(self, entry: Dict) -> List[Dict]:
        """检测链接失效"""
        results = []
        answer = entry.get("answer", "")
        urls = extract_urls(answer)
        
        for url in urls:
            for pattern in self.INTERNAL_URL_PATTERNS:
                if re.match(pattern, url):
                    results.append({
                        "problem_type": "dead_link",
                        "issue_detail": f"规则匹配：链接指向内部/测试地址（{url}），外部用户无法访问",
                        "severity": "major",
                    })
                    break
        
        # 检查旧域名
        if re.search(r'old-domain', answer):
            if not any(r["problem_type"] == "dead_link" for r in results):
                results.append({
                    "problem_type": "dead_link",
                    "issue_detail": "规则匹配：链接指向旧域名（old-domain），可能已失效",
                    "severity": "major",
                })
        
        return results
    
    def _check_qa_mismatch(self, entry: Dict) -> List[Dict]:
        """检测问答不匹配"""
        results = []
        question = entry.get("question", "")
        answer = entry.get("answer", "")
        
        # 检查问题关键词与回答主题是否相关
        # 如果问题问核心操作/对象但回答里完全没有提到相关词
        topic_keywords = {
            "退货": ["退货", "退回", "退款", "寄回"],
            "换货": ["换货", "更换", "调换"],
            "运费": ["运费", "邮费", "快递费", "承担"],
            "支付": ["支付", "付款", "结算"],
            "密码": ["密码", "验证"],
            "配送": ["配送", "送达", "发货", "快递"],
            "开发票": ["发票", "抬头", "税号"],
            "发票": ["发票", "抬头", "税号"],
        }
        
        for topic, keywords in topic_keywords.items():
            if topic in question:
                if not any(kw in answer for kw in keywords):
                    results.append({
                        "problem_type": "qa_mismatch",
                        "issue_detail": f"规则匹配：问题涉及「{topic}」，但回答中未出现相关关键词",
                        "severity": "critical",
                    })
                    break
        
        return results
    
    def _check_incomplete(self, entry: Dict) -> List[Dict]:
        """检测回答不完整"""
        results = []
        question = entry.get("question", "")
        answer = entry.get("answer", "")
        
        # 空答案直接判定为不完整
        if answer.strip() == "":
            results.append({
                "problem_type": "incomplete",
                "issue_detail": "规则匹配：回答为空，完全未提供任何信息",
                "severity": "major",
            })
            return results
        
        # 如果问题包含多个方面但回答很短
        aspect_markers = ["和", "与", "以及", "分别", "还是", "哪种"]
        aspect_count = sum(1 for m in aspect_markers if m in question)
        
        if aspect_count >= 1 and len(answer) < 30:
            results.append({
                "problem_type": "incomplete",
                "issue_detail": f"规则匹配：问题涉及多个方面，但回答仅{len(answer)}字，可能未覆盖全部方面",
                "severity": "major",
            })
        
        # 检查是否只回答了一部分
        # 如果问题中有"怎么"但回答中没有步骤性内容（阈值较低，仅抓明显缺失）
        if ("怎么" in question or "如何" in question or "流程" in question) and len(answer) < 20:
            has_steps = any(marker in answer for marker in ["1.", "2.", "步骤", "首先", "然后", "接着", "点击", "输入", "选择"])
            if not has_steps:
                results.append({
                    "problem_type": "incomplete",
                    "issue_detail": "规则匹配：问题询问操作方法，但回答缺少步骤说明",
                    "severity": "major",
                })
        
        return results
    
    def _check_duplicates(self, entries: List[Dict]) -> List[Dict]:
        """检测内容重复（跨条目）"""
        results = []
        checked = set()
        
        for i, e1 in enumerate(entries):
            for j, e2 in enumerate(entries):
                if i >= j:
                    continue
                pair_key = f"{e1['id']}-{e2['id']}"
                if pair_key in checked:
                    continue
                
                # 问题相似度
                q_sim = text_similarity(e1["question"], e2["question"])
                # 答案相似度
                a_sim = text_similarity(e1.get("answer", ""), e2.get("answer", ""))
                
                # 高相似度判定为重复：
                # 1) 问题与答案都高度相似；或 2) 问题完全相同（即使答案不同，也属于重复提问）
                is_duplicate = (q_sim > 0.93 and a_sim > 0.97) or (q_sim == 1.0 and len(e1["question"]) > 3)
                if is_duplicate:
                    checked.add(pair_key)
                    results.append({
                        "entry_id": e1["id"],
                        "question": e1["question"],
                        "category": e1["category"],
                        "problem_type": "duplicate",
                        "issue_detail": f"与条目 {e2['id']}（「{e2['question'][:20]}...」）高度重复（问题相似度{q_sim:.0%}，答案相似度{a_sim:.0%}）",
                        "severity": "minor",
                        "detection_method": "rule",
                    })
                    results.append({
                        "entry_id": e2["id"],
                        "question": e2["question"],
                        "category": e2["category"],
                        "problem_type": "duplicate",
                        "issue_detail": f"与条目 {e1['id']}（「{e1['question'][:20]}...」）高度重复（问题相似度{q_sim:.0%}，答案相似度{a_sim:.0%}）",
                        "severity": "minor",
                        "detection_method": "rule",
                    })
        
        return results
    
    def _check_contradictions(self, entries: List[Dict]) -> List[Dict]:
        """检测条目矛盾（跨条目）"""
        results = []
        
        # 按问题相似度分组
        groups = defaultdict(list)
        for entry in entries:
            # 用问题的n-gram作为分组键
            q = entry.get("question", "")
            ngrams = char_ngrams(q, 3)
            # 使用最常见的n-gram作为键
            for ng in list(ngrams)[:3]:
                groups[ng].append(entry)
        
        # 在相似问题中检查答案矛盾
        checked_pairs = set()
        for group_entries in groups.values():
            if len(group_entries) < 2:
                continue
            
            for i, e1 in enumerate(group_entries):
                for j, e2 in enumerate(group_entries):
                    if i >= j:
                        continue
                    
                    pair_key = f"{e1['id']}-{e2['id']}"
                    if pair_key in checked_pairs:
                        continue
                    
                    q_sim = text_similarity(e1["question"], e2["question"])
                    if q_sim < 0.85:
                        continue
                    
                    a_sim = text_similarity(e1.get("answer", ""), e2.get("answer", ""))
                    
                    # 问题高度相似但答案不同 -> 可能矛盾
                    # 问题完全相同时，阈值放宽以捕获同题不同答的情况
                    contradiction_threshold = 0.65 if q_sim >= 0.99 else 0.35
                    if q_sim > 0.85 and a_sim < contradiction_threshold and len(e1.get("answer","")) > 20 and len(e2.get("answer","")) > 20:
                        checked_pairs.add(pair_key)
                        
                        # 提取数字进行对比
                        nums1 = set(re.findall(r'\d+', e1.get("answer", "")))
                        nums2 = set(re.findall(r'\d+', e2.get("answer", "")))
                        common_nums = nums1 & nums2
                        diff_nums = (nums1 | nums2) - (nums1 & nums2)
                        
                        issue_desc = f"与条目 {e2['id']}（「{e2['question'][:20]}...」）对相似问题给出不同答案"
                        if diff_nums and len(diff_nums) > 0:
                            issue_desc += f"，数值差异: {e1['id']}含{nums1}, {e2['id']}含{nums2}"
                        
                        results.append({
                            "entry_id": e1["id"],
                            "question": e1["question"],
                            "category": e1["category"],
                            "problem_type": "contradiction",
                            "issue_detail": issue_desc,
                            "severity": "critical",
                            "detection_method": "rule",
                            "related_entry": e2["id"],
                        })
        
        # 去重：同一entry_id的同一问题类型只保留一条
        seen = {}
        deduped = []
        for r in results:
            key = f"{r['entry_id']}-{r['problem_type']}"
            if key not in seen:
                seen[key] = True
                deduped.append(r)
        
        return deduped


# ============================================================
# LLM 检测器（支持 mock 模式）
# ============================================================

class LLMDetector:
    """基于 LLM 的问题检测器，支持 mock 模式和真实 API"""
    
    def __init__(self, mode: str = "mock", api_key: str = "", api_base: str = "", model: str = "gpt-4o-mini"):
        """
        Args:
            mode: "mock" 使用模拟返回，"api" 调用真实 LLM API
            api_key: API密钥（api模式需要）
            api_base: API地址（api模式需要）
            model: 模型名称
        """
        self.mode = mode
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
    
    def detect(self, entries: List[Dict]) -> List[Dict]:
        """对知识库条目进行 LLM 检测"""
        if self.mode == "mock":
            return self._mock_detect(entries)
        else:
            return self._api_detect(entries)
    
    def _mock_detect(self, entries: List[Dict]) -> List[Dict]:
        """
        Mock模式：基于规则补充检测，模拟LLM返回结果
        对规则检测可能遗漏的语义问题进行补充检测
        """
        results = []
        
        for entry in entries:
            question = entry.get("question", "")
            answer = entry.get("answer", "")
            
            # 1. 语义层面的问答不匹配检测
            # 规则检测可能漏掉的细微不匹配
            if self._mock_check_semantic_mismatch(question, answer):
                results.append({
                    "entry_id": entry["id"],
                    "question": question,
                    "category": entry["category"],
                    "problem_type": "qa_mismatch",
                    "issue_detail": "[LLM] 语义分析：回答内容与问题主题不相关，答非所问",
                    "severity": "critical",
                    "detection_method": "llm",
                })
            
            # 2. 语义层面的信息模糊检测
            if self._mock_check_semantic_vague(question, answer):
                results.append({
                    "entry_id": entry["id"],
                    "question": question,
                    "category": entry["category"],
                    "problem_type": "vague",
                    "issue_detail": "[LLM] 语义分析：回答缺少具体数据、操作步骤或明确指引，信息密度低",
                    "severity": "major",
                    "detection_method": "llm",
                })
            
            # 3. 语义层面的回答不完整检测
            if self._mock_check_semantic_incomplete(question, answer):
                results.append({
                    "entry_id": entry["id"],
                    "question": question,
                    "category": entry["category"],
                    "problem_type": "incomplete",
                    "issue_detail": "[LLM] 语义分析：回答未覆盖问题涉及的关键方面",
                    "severity": "major",
                    "detection_method": "llm",
                })
            
            # 4. 过时内容补充检测
            if self._mock_check_outdated(question, answer):
                results.append({
                    "entry_id": entry["id"],
                    "question": question,
                    "category": entry["category"],
                    "problem_type": "outdated",
                    "issue_detail": "[LLM] 语义分析：回答中引用了过时的活动、政策或产品信息",
                    "severity": "major",
                    "detection_method": "llm",
                })
        
        return results
    
    def _mock_check_semantic_mismatch(self, question: str, answer: str) -> bool:
        """Mock: 语义层面的问答不匹配"""
        # 检查问题关键词是否在回答中出现
        topic_pairs = [
            (["退货运费", "运费怎么算", "运费谁"], ["运费", "邮费", "快递费", "承担"]),
            (["支付密码", "支付密码"], ["支付密码", "支付"]),
            (["配送范围", "送到乡镇", "送到农村"], ["配送", "乡镇", "农村", "范围", "地址"]),
            (["退货政策", "无理由退货", "七天无理由"], ["退货", "无理由", "七天", "7天"]),
            (["修改地址", "改地址"], ["地址", "修改", "更改"]),
            (["开发票", "发票"], ["发票", "抬头", "税号"]),
        ]
        
        for q_keywords, a_keywords in topic_pairs:
            if any(kw in question for kw in q_keywords):
                if not any(kw in answer for kw in a_keywords):
                    return True
        return False
    
    def _mock_check_semantic_vague(self, question: str, answer: str) -> bool:
        """Mock: 语义层面的信息模糊"""
        # 检查回答是否包含具体的数值
        has_numbers = bool(re.search(r'\d+', answer))
        # 检查回答是否包含操作步骤
        has_steps = any(marker in answer for marker in ["1.", "2.", "步骤", "首先", "然后", "接着", "点击"])
        
        # 如果问题询问具体信息但回答没有数值和步骤
        specific_questions = ["多少", "几天", "多久", "什么时候", "费用", "价格", "时间", "门槛", "条件"]
        if any(sq in question for sq in specific_questions):
            if not has_numbers and not has_steps and len(answer) < 40:
                return True
        
        return False
    
    def _mock_check_semantic_incomplete(self, question: str, answer: str) -> bool:
        """Mock: 语义层面的回答不完整（仅检测明显缺失）"""
        # 空答案由规则检测覆盖
        if not answer.strip():
            return False
        
        # 检查问题中是否有"和"/"与"/"分别"等多方面标记
        multi_aspect = any(m in question for m in ["和", "与", "以及", "分别", "还是"])
        
        if multi_aspect and len(answer) < 25:
            return True
        
        # 检查"怎么"类问题是否有步骤
        if ("怎么" in question or "如何" in question) and len(answer) < 18:
            has_steps = any(m in answer for m in ["1.", "步骤", "首先", "然后", "点击", "输入", "选择"])
            if not has_steps:
                return True
        
        return False
    
    def _mock_check_outdated(self, question: str, answer: str) -> bool:
        """Mock: 过时内容补充检测"""
        text = question + " " + answer
        outdated_indicators = [
            "2021年", "2022年", "2020年",
            "疫情", "封控", "隔离",
            "iPhone 12", "iPhone 13", "iPhone 11",
        ]
        return any(ind in text for ind in outdated_indicators)
    
    def _api_detect(self, entries: List[Dict]) -> List[Dict]:
        """调用真实 LLM API 进行检测"""
        try:
            import urllib.request
            import urllib.error
        except ImportError:
            print("  [LLM] 无法导入 urllib，回退到 mock 模式")
            return self._mock_detect(entries)
        
        results = []
        batch_size = 5  # 每次发送5条
        
        for i in range(0, len(entries), batch_size):
            batch = entries[i:i+batch_size]
            prompt = self._build_prompt(batch)
            
            try:
                response = self._call_api(prompt)
                batch_results = self._parse_response(response, batch)
                results.extend(batch_results)
                print(f"  [LLM] 已检测 {min(i+batch_size, len(entries))}/{len(entries)}")
            except Exception as e:
                print(f"  [LLM] 批次 {i//batch_size+1} 检测失败: {e}")
                # 失败时回退到 mock
                batch_results = self._mock_detect(batch)
                results.extend(batch_results)
        
        return results
    
    def _build_prompt(self, batch: List[Dict]) -> str:
        """构建LLM检测提示词"""
        entries_text = ""
        for e in batch:
            entries_text += f"[{e['id']}] 问题: {e['question']}\n回答: {e.get('answer', '')}\n\n"
        
        prompt = f"""你是一个知识库质量检测专家。请分析以下FAQ条目是否存在质量问题。

问题类型定义：
1. outdated: 内容过时（引用旧活动、旧政策、已下线功能）
2. contradiction: 条目矛盾（与知识库其他条目对同一问题给出矛盾答案）
3. duplicate: 内容重复（与知识库其他条目高度相似）
4. incomplete: 回答不完整（未覆盖问题涉及的关键方面）
5. format_issue: 格式不规范（多余空行、不一致间距、混乱分隔符）
6. qa_mismatch: 问答不匹配（答非所问）
7. vague: 信息模糊（过于笼统，缺少具体数据或步骤）
8. dead_link: 链接失效（包含失效链接或内网地址）

请对每条有问题的条目输出JSON格式：
[{{"id": "KB_0001", "problem_type": "vague", "issue_detail": "具体问题描述"}}]

如果没有问题，不要输出该条目。

待检测条目：
{entries_text}
"""
        return prompt
    
    def _call_api(self, prompt: str) -> str:
        """调用LLM API"""
        data = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }).encode("utf-8")
        
        req = urllib.request.Request(
            f"{self.api_base}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    
    def _parse_response(self, response: str, batch: List[Dict]) -> List[Dict]:
        """解析LLM返回结果"""
        results = []
        entry_map = {e["id"]: e for e in batch}
        
        # 尝试提取JSON
        try:
            # 找到JSON数组
            match = re.search(r'\[.*\]', response, re.DOTALL)
            if match:
                items = json.loads(match.group())
                for item in items:
                    eid = item.get("id", "")
                    if eid in entry_map:
                        entry = entry_map[eid]
                        pt = ProblemType.get_by_code(item.get("problem_type", ""))
                        results.append({
                            "entry_id": eid,
                            "question": entry["question"],
                            "category": entry["category"],
                            "problem_type": item.get("problem_type", "unknown"),
                            "issue_detail": f"[LLM] {item.get('issue_detail', '检测到问题')}",
                            "severity": pt["severity"] if pt else "major",
                            "detection_method": "llm",
                        })
        except (json.JSONDecodeError, AttributeError):
            pass
        
        return results


# ============================================================
# 组合检测器
# ============================================================

class KBDetector:
    """知识库检测器：组合规则检测和LLM检测"""
    
    def __init__(self, llm_mode: str = "mock", api_key: str = "", api_base: str = "", business_context: str = ""):
        self.rule_detector = RuleDetector(business_context=business_context)
        self.llm_detector = LLMDetector(mode=llm_mode, api_key=api_key, api_base=api_base)
    
    def detect(self, entries: List[Dict]) -> Dict[str, Any]:
        """
        运行完整检测
        
        Returns:
            {
                "results": [检测到的问题列表],
                "stats": {统计信息},
                "problem_entries": {entry_id -> [问题列表]}
            }
        """
        print("=" * 60)
        print("知识库质量检测开始")
        print(f"总条目数: {len(entries)}")
        print("=" * 60)
        
        # 1. 规则检测
        print("\n[1/2] 运行规则检测...")
        rule_results = self.rule_detector.detect_all(entries)
        print(f"  规则检测发现 {len(rule_results)} 个问题")
        
        # 2. LLM检测
        print(f"\n[2/2] 运行LLM检测（模式: {self.llm_detector.mode}）...")
        llm_results = self.llm_detector.detect(entries)
        print(f"  LLM检测发现 {len(llm_results)} 个问题")
        
        # 3. 合并结果（去重：同一entry同一问题类型，保留详细信息更全的）
        all_results = self._merge_results(rule_results, llm_results)
        
        # 4. 按entry分组
        problem_entries = defaultdict(list)
        for r in all_results:
            problem_entries[r["entry_id"]].append(r)
        
        # 5. 统计
        stats = self._compute_stats(all_results, entries, problem_entries)
        
        print("\n" + "=" * 60)
        print("检测完成！")
        print(f"问题条目数: {len(problem_entries)} / {len(entries)}")
        print(f"问题总数: {len(all_results)}")
        print("=" * 60)
        
        return {
            "results": all_results,
            "stats": stats,
            "problem_entries": dict(problem_entries),
        }
    
    def _merge_results(self, rule_results: List[Dict], llm_results: List[Dict]) -> List[Dict]:
        """合并规则检测和LLM检测结果，去重"""
        # 用 (entry_id, problem_type) 作为去重键
        # 如果两者都检测到同一问题，保留两条但标记来源
        # 如果只有一方检测到，也保留
        merged = {}
        
        for r in rule_results + llm_results:
            key = f"{r['entry_id']}-{r['problem_type']}"
            if key not in merged:
                merged[key] = r
            else:
                # 如果LLM也检测到了，标记为双重确认
                existing = merged[key]
                if existing["detection_method"] != r["detection_method"]:
                    existing["confirmed_by"] = "rule+llm"
                    # 保留更详细的issue_detail
                    if len(r["issue_detail"]) > len(existing["issue_detail"]):
                        existing["issue_detail"] = r["issue_detail"]
        
        return list(merged.values())
    
    def _compute_stats(self, results: List[Dict], entries: List[Dict], problem_entries: Dict) -> Dict:
        """计算统计信息"""
        # 按问题类型统计
        type_counts = defaultdict(int)
        for r in results:
            type_counts[r["problem_type"]] += 1
        
        # 按严重等级统计
        severity_counts = defaultdict(int)
        for r in results:
            severity_counts[r["severity"]] += 1
        
        # 按分类统计
        category_counts = defaultdict(int)
        for r in results:
            category_counts[r["category"]] += 1
        
        # 按检测方法统计
        method_counts = defaultdict(int)
        for r in results:
            method_counts[r["detection_method"]] += 1
        
        return {
            "total_entries": len(entries),
            "problem_entry_count": len(problem_entries),
            "normal_entry_count": len(entries) - len(problem_entries),
            "total_issues": len(results),
            "by_type": dict(type_counts),
            "by_severity": dict(severity_counts),
            "by_category": dict(category_counts),
            "by_method": dict(method_counts),
        }
