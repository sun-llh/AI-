# -*- coding: utf-8 -*-
"""
知识库问题条目分类体系定义

定义8类问题类型，每类包含：
- code: 问题类型代码
- name: 中文名称
- description: 问题描述
- impact: 业务影响
- severity: 默认严重等级 (critical/major/minor)
- governance_action: 默认治理动作
"""


class ProblemType:
    """问题类型定义"""
    
    OUTDATED = {
        "code": "outdated",
        "name": "内容过时",
        "description": "引用了已过期的活动、旧版政策、已下线的功能或旧年份的信息",
        "impact": "向用户提供过期信息，导致错误的操作指引，降低信任度",
        "severity": "major",
        "governance_action": "修改",
    }
    
    CONTRADICTION = {
        "code": "contradiction",
        "name": "条目矛盾",
        "description": "不同条目对同一问题给出了相互矛盾的回答",
        "impact": "用户收到矛盾信息后产生困惑，客服自动回复可能给出错误答案",
        "severity": "critical",
        "governance_action": "修改",
    }
    
    DUPLICATE = {
        "code": "duplicate",
        "name": "内容重复",
        "description": "问题表述不同但实际内容高度相似的条目",
        "impact": "增加维护成本，容易在更新时遗漏导致信息不一致",
        "severity": "minor",
        "governance_action": "合并",
    }
    
    INCOMPLETE = {
        "code": "incomplete",
        "name": "回答不完整",
        "description": "回答未能覆盖问题涉及的关键方面，缺少重要信息",
        "impact": "用户无法获得完整解答，需二次咨询，增加客服压力",
        "severity": "major",
        "governance_action": "修改",
    }
    
    FORMAT_ISSUE = {
        "code": "format_issue",
        "name": "格式不规范",
        "description": "存在多余换行、不一致的间距、混乱的分隔符或标点等格式问题",
        "impact": "影响阅读体验，在客服自动回复中显示异常",
        "severity": "minor",
        "governance_action": "修改",
    }
    
    QA_MISMATCH = {
        "code": "qa_mismatch",
        "name": "问答不匹配",
        "description": "回答内容与问题无关或答非所问",
        "impact": "用户无法获得有效帮助，严重影响用户体验",
        "severity": "critical",
        "governance_action": "修改",
    }
    
    VAGUE = {
        "code": "vague",
        "name": "信息模糊",
        "description": "回答过于笼统，缺乏具体的操作步骤、数值或指引",
        "impact": "用户无法据此采取行动，降低知识库的实用价值",
        "severity": "major",
        "governance_action": "修改",
    }
    
    DEAD_LINK = {
        "code": "dead_link",
        "name": "链接失效",
        "description": "回答中包含可能失效的链接，或指向内网/测试地址",
        "impact": "用户点击后无法访问，导致信息断层",
        "severity": "major",
        "governance_action": "修改",
    }
    
    ALL_TYPES = [
        OUTDATED, CONTRADICTION, DUPLICATE, INCOMPLETE,
        FORMAT_ISSUE, QA_MISMATCH, VAGUE, DEAD_LINK
    ]
    
    @classmethod
    def get_by_code(cls, code):
        """根据code获取问题类型"""
        for pt in cls.ALL_TYPES:
            if pt["code"] == code:
                return pt
        return None
    
    @classmethod
    def get_name(cls, code):
        """获取中文名称"""
        pt = cls.get_by_code(code)
        return pt["name"] if pt else code


# 严重等级权重（用于计算优先级分数）
SEVERITY_WEIGHT = {
    "critical": 3,
    "major": 2,
    "minor": 1,
}

# 严重等级中文
SEVERITY_LABEL = {
    "critical": "严重",
    "major": "重要",
    "minor": "一般",
}
