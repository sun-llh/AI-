# -*- coding: utf-8 -*-
"""
治理建议生成器

根据检测到的问题类型，为每个问题条目生成具体的改进建议：
- 修改：对内容进行修订
- 合并：将重复条目合并为一条
- 删除：删除无价值的条目
- 新增：建议补充缺失的内容
"""

from typing import List, Dict, Any
from .problem_types import ProblemType, SEVERITY_WEIGHT


class GovernanceAdvisor:
    """治理建议生成器"""
    
    # 治理动作模板
    ACTION_TEMPLATES = {
        "outdated": {
            "action": "修改",
            "suggestion": "更新为当前有效的活动信息、政策或产品名称。建议建立定期巡检机制，每季度检查涉及活动、价格、政策的条目。如活动已结束，应更新为通用说明或标注「该活动已结束」。",
            "priority_boost": 0,
        },
        "contradiction": {
            "action": "修改",
            "suggestion": "核实正确信息后统一口径。建议以最新政策为准，修改矛盾的条目使其一致。对于涉及数值（如天数、金额、门槛）的矛盾，需与业务方确认当前正确值。同时建议建立知识库编辑审核流程，避免新增矛盾。",
            "priority_boost": 1,
        },
        "duplicate": {
            "action": "合并",
            "suggestion": "将重复条目合并为一条，保留表述最清晰、信息最完整的版本，删除其余条目。合并后需确认关键词覆盖，确保用户不同表述方式都能匹配到。",
            "priority_boost": -1,
        },
        "incomplete": {
            "action": "修改",
            "suggestion": "补充回答中缺失的关键信息。建议参考同分类下信息完整的条目，确保覆盖问题的所有方面。对于操作类问题，应提供分步骤说明。",
            "priority_boost": 0,
        },
        "format_issue": {
            "action": "修改",
            "suggestion": "统一格式规范：使用一致的标点和分隔符，删除多余空行和空格，长文本按逻辑分段。建议制定知识库编辑规范文档。",
            "priority_boost": -1,
        },
        "qa_mismatch": {
            "action": "修改",
            "suggestion": "重新编写回答，确保直接回应问题内容。如果原回答有价值，可考虑拆分为新条目（将原回答配对到正确的问题）。建议增加问答匹配度校验。",
            "priority_boost": 1,
        },
        "vague": {
            "action": "修改",
            "suggestion": "补充具体的数值、时间范围、操作步骤或参考链接。将模糊表述替换为明确指引，如将「几天」改为「3-5个工作日」。",
            "priority_boost": 0,
        },
        "dead_link": {
            "action": "修改",
            "suggestion": "更换为有效的外部链接，或直接将链接内容内联到回答中。移除内网/测试地址。建议定期进行链接有效性检查。",
            "priority_boost": 0,
        },
    }
    
    def __init__(self):
        pass
    
    def generate_suggestions(self, detection_result: Dict[str, Any], entries: List[Dict]) -> List[Dict]:
        """
        为所有问题条目生成治理建议
        
        Returns:
            建议列表，每条包含：
            - entry_id, question, category
            - problems: [问题列表]
            - action: 治理动作
            - suggestion: 具体建议
            - priority: 优先级分数（1-10）
            - priority_label: 优先级标签
        """
        suggestions = []
        entry_map = {e["id"]: e for e in entries}
        problem_entries = detection_result.get("problem_entries", {})
        
        for entry_id, problems in problem_entries.items():
            entry = entry_map.get(entry_id, {})
            
            # 综合多个问题生成建议
            advice = self._generate_for_entry(entry, problems)
            suggestions.append(advice)
        
        # 按优先级排序
        suggestions.sort(key=lambda x: x["priority"], reverse=True)
        
        return suggestions
    
    def _generate_for_entry(self, entry: Dict, problems: List[Dict]) -> Dict:
        """为单个条目生成治理建议"""
        # 收集所有问题类型
        problem_types = list(set(p["problem_type"] for p in problems))
        
        # 确定主问题类型（取严重等级最高的）
        primary_type = max(problem_types, key=lambda t: SEVERITY_WEIGHT.get(
            ProblemType.get_by_code(t)["severity"] if ProblemType.get_by_code(t) else "major",
            2
        ))
        
        # 获取建议模板
        template = self.ACTION_TEMPLATES.get(primary_type, {
            "action": "修改",
            "suggestion": "请人工审核该条目内容。",
            "priority_boost": 0,
        })
        
        # 生成综合建议
        problem_details = []
        for p in problems:
            pt = ProblemType.get_by_code(p["problem_type"])
            type_name = pt["name"] if pt else p["problem_type"]
            problem_details.append(f"[{type_name}] {p['issue_detail']}")
        
        # 计算优先级
        priority = self._compute_priority(problems, template.get("priority_boost", 0))
        
        # 特殊处理：如果同时有多个问题类型
        if len(problem_types) > 1:
            action = "修改"
            suggestion = f"该条目存在{len(problem_types)}类问题（{', '.join(ProblemType.get_by_code(t)['name'] for t in problem_types if ProblemType.get_by_code(t))}）。建议优先解决最严重的问题：{template['suggestion']}"
        else:
            action = template["action"]
            suggestion = template["suggestion"]
        
        return {
            "entry_id": entry.get("id", ""),
            "question": entry.get("question", ""),
            "category": entry.get("category", ""),
            "problem_types": problem_types,
            "problem_details": problem_details,
            "action": action,
            "suggestion": suggestion,
            "priority": priority,
            "priority_label": self._priority_label(priority),
            "answer_preview": entry.get("answer", "")[:100] + "..." if len(entry.get("answer", "")) > 100 else entry.get("answer", ""),
        }
    
    def _compute_priority(self, problems: List[Dict], boost: int) -> int:
        """
        计算优先级分数（1-10）
        基于问题严重等级、问题数量、是否双重确认等
        """
        base = 0
        for p in problems:
            sev = p.get("severity", "major")
            base += SEVERITY_WEIGHT.get(sev, 2)
        
        # 多重问题加分
        if len(problems) > 1:
            base += 1
        
        # 双重确认加分
        for p in problems:
            if p.get("confirmed_by") == "rule+llm":
                base += 1
                break
        
        # 模板加成
        base += boost
        
        # 归一化到1-10
        return max(1, min(10, base))
    
    def _priority_label(self, priority: int) -> str:
        """优先级标签"""
        if priority >= 8:
            return "P0-紧急"
        elif priority >= 6:
            return "P1-高"
        elif priority >= 4:
            return "P2-中"
        else:
            return "P3-低"
    
    def generate_coverage_gaps(self, entries: List[Dict]) -> List[Dict]:
        """
        分析覆盖缺失：识别知识库中缺少的常见问题类型
        
        基于电商客服场景的常见问题清单，检查知识库是否覆盖
        """
        # 电商客服核心问题清单
        expected_topics = [
            ("订单管理", "如何查看订单状态"),
            ("订单管理", "如何取消订单"),
            ("订单管理", "修改收货地址"),
            ("订单管理", "订单超时未付款"),
            ("退换货", "七天无理由退货条件"),
            ("退换货", "退货流程"),
            ("退换货", "退款到账时间"),
            ("退换货", "质量问题退换货"),
            ("支付问题", "支持的支付方式"),
            ("支付问题", "付款失败处理"),
            ("支付问题", "优惠券使用规则"),
            ("支付问题", "发票开具"),
            ("物流配送", "配送时效"),
            ("物流配送", "运费计算"),
            ("物流配送", "物流查询"),
            ("物流配送", "快递丢失处理"),
            ("商品咨询", "商品真伪验证"),
            ("商品咨询", "商品尺寸选择"),
            ("商品咨询", "缺货补货通知"),
            ("账户安全", "忘记密码"),
            ("账户安全", "修改绑定手机"),
            ("账户安全", "账户被盗处理"),
            ("优惠活动", "新人优惠"),
            ("优惠活动", "积分规则"),
            ("优惠活动", "会员等级"),
            ("售后服务", "保修政策"),
            ("售后服务", "维修申请流程"),
            ("会员权益", "会员权益说明"),
            ("会员权益", "积分获取方式"),
            ("发票相关", "增值税专票"),
        ]
        
        # 检查覆盖情况
        from .detector import text_similarity
        
        gaps = []
        for cat, expected_q in expected_topics:
            best_sim = 0
            best_entry = None
            for entry in entries:
                # 优先匹配同分类，若分类不匹配也允许全局匹配
                same_cat = entry.get("category") == cat
                sim = text_similarity(expected_q, entry.get("question", ""))
                # 同分类条目相似度权重更高
                effective_sim = sim * 1.2 if same_cat else sim
                if effective_sim > best_sim:
                    best_sim = effective_sim
                    best_entry = entry
            
            if best_sim < 0.4:
                gaps.append({
                    "category": cat,
                    "missing_topic": expected_q,
                    "best_match_similarity": best_sim,
                    "best_match_entry": best_entry["id"] if best_entry else None,
                    "suggestion": f"建议新增「{expected_q}」相关条目",
                    "action": "新增",
                })
        
        return gaps
