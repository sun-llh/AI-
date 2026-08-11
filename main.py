# -*- coding: utf-8 -*-
"""
知识库条目质量治理工具 - 主入口

用法:
    # Mock模式（默认，无需API密钥）
    python main.py

    # 使用真实LLM API
    python main.py --llm api --api-key YOUR_KEY --api-base https://api.openai.com/v1

    # 指定输入数据文件
    python main.py --input data/kb_data.json

    # 仅输出JSON报告
    python main.py --format json
"""

import argparse
import json
import os
import sys
from datetime import datetime

# 将src目录加入路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import KBDetector, GovernanceAdvisor, ReportGenerator


def load_entries(data_path: str) -> list:
    """加载知识库数据"""
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 确保每条数据有必要字段
    for entry in data:
        if "id" not in entry:
            entry["id"] = f"KB_{hash(entry.get('question', ''))}"
        if "answer" not in entry:
            entry["answer"] = ""
        if "category" not in entry:
            entry["category"] = "未分类"
    
    return data


def load_business_context(context_path: str) -> str:
    """加载业务规则摘要文本"""
    if not context_path or not os.path.exists(context_path):
        return ""
    with open(context_path, "r", encoding="utf-8") as f:
        return f.read()


def save_json_report(detection_result: dict, suggestions: list, coverage_gaps: list, output_path: str):
    """保存JSON格式的报告"""
    report = {
        "generated_at": datetime.now().isoformat(),
        "detection_stats": detection_result["stats"],
        "problem_entries": detection_result["problem_entries"],
        "all_results": detection_result["results"],
        "governance_suggestions": suggestions,
        "coverage_gaps": coverage_gaps,
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\nJSON报告已保存至: {output_path}")


def save_html_report(html_content: str, output_path: str):
    """保存HTML格式的报告"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"HTML报告已保存至: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="知识库条目质量治理工具")
    parser.add_argument("--input", "-i", default="data/kb_data.json", 
                        help="知识库数据文件路径 (默认: data/kb_data.json)")
    parser.add_argument("--context", "-c", default="",
                        help="业务规则摘要文件路径（Markdown格式），用于检测内容过时/矛盾")
    parser.add_argument("--llm", choices=["mock", "api"], default="mock",
                        help="LLM检测模式: mock(模拟) 或 api(真实API) (默认: mock)")
    parser.add_argument("--api-key", default="", help="LLM API密钥")
    parser.add_argument("--api-base", default="https://api.openai.com/v1", 
                        help="LLM API地址 (默认: https://api.openai.com/v1)")
    parser.add_argument("--model", default="gpt-4o-mini", help="LLM模型名称")
    parser.add_argument("--format", "-f", choices=["html", "json", "both"], default="both",
                        help="输出格式: html, json, 或 both (默认: both)")
    parser.add_argument("--output-dir", "-o", default="reports",
                        help="报告输出目录 (默认: reports)")
    
    args = parser.parse_args()
    
    # 路径处理
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base_dir, args.input) if not os.path.isabs(args.input) else args.input
    context_path = os.path.join(base_dir, args.context) if args.context and not os.path.isabs(args.context) else args.context
    output_dir = os.path.join(base_dir, args.output_dir) if not os.path.isabs(args.output_dir) else args.output_dir
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 加载数据
    print(f"正在加载知识库数据: {data_path}")
    entries = load_entries(data_path)
    print(f"已加载 {len(entries)} 条知识库条目")
    
    # 加载业务规则
    business_context = load_business_context(context_path)
    if business_context:
        print(f"已加载业务规则摘要: {context_path}")
    
    # 运行检测
    detector = KBDetector(llm_mode=args.llm, api_key=args.api_key, api_base=args.api_base,
                          business_context=business_context)
    detection_result = detector.detect(entries)
    
    # 生成治理建议
    print("\n正在生成治理建议...")
    advisor = GovernanceAdvisor()
    suggestions = advisor.generate_suggestions(detection_result, entries)
    
    # 分析覆盖缺失
    print("正在分析覆盖缺失...")
    coverage_gaps = advisor.generate_coverage_gaps(entries)
    
    # 打印摘要
    stats = detection_result["stats"]
    print("\n" + "=" * 60)
    print("治理报告摘要")
    print("=" * 60)
    print(f"  知识库总条目: {stats['total_entries']}")
    print(f"  问题条目数: {stats['problem_entry_count']}")
    print(f"  正常条目数: {stats['normal_entry_count']}")
    print(f"  健康度: {round((1 - stats['problem_entry_count']/stats['total_entries'])*100, 1)}%")
    print(f"  问题总数: {stats['total_issues']}")
    print(f"\n  问题类型分布:")
    for ptype, count in sorted(stats.get("by_type", {}).items(), key=lambda x: -x[1]):
        from src.problem_types import ProblemType
        pt = ProblemType.get_by_code(ptype)
        name = pt["name"] if pt else ptype
        print(f"    {name}: {count}")
    print(f"\n  严重等级分布:")
    from src.problem_types import SEVERITY_LABEL
    for sev, count in sorted(stats.get("by_severity", {}).items(), key=lambda x: -x[1]):
        print(f"    {SEVERITY_LABEL.get(sev, sev)}: {count}")
    print(f"\n  覆盖缺失: {len(coverage_gaps)} 个主题")
    print(f"  治理建议: {len(suggestions)} 条")
    print("=" * 60)
    
    # 保存报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if args.format in ["html", "both"]:
        reporter = ReportGenerator()
        html_content = reporter.generate(detection_result, suggestions, coverage_gaps, entries)
        html_path = os.path.join(output_dir, f"governance_report_{timestamp}.html")
        save_html_report(html_content, html_path)
    
    if args.format in ["json", "both"]:
        json_path = os.path.join(output_dir, f"governance_report_{timestamp}.json")
        save_json_report(detection_result, suggestions, coverage_gaps, json_path)
    
    print(f"\n✓ 治理报告生成完成！")
    if args.format in ["html", "both"]:
        print(f"  HTML报告: {os.path.join(output_dir, f'governance_report_{timestamp}.html')}")
    if args.format in ["json", "both"]:
        print(f"  JSON报告: {os.path.join(output_dir, f'governance_report_{timestamp}.json')}")


if __name__ == "__main__":
    main()
