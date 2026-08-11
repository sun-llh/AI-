# -*- coding: utf-8 -*-
"""
治理报告生成器

生成HTML格式的治理报告，包含：
1. 摘要概览
2. 问题分布统计（图表）
3. 问题条目明细
4. 治理建议
5. 覆盖缺失分析
6. 优先级处理建议
"""

from typing import List, Dict, Any
from datetime import datetime
from .problem_types import ProblemType, SEVERITY_LABEL


class ReportGenerator:
    """HTML报告生成器"""
    
    def __init__(self):
        self.color_map = {
            "critical": "#e74c3c",
            "major": "#f39c12",
            "minor": "#3498db",
        }
        self.type_colors = {
            "outdated": "#e74c3c",
            "contradiction": "#c0392b",
            "duplicate": "#3498db",
            "incomplete": "#f39c12",
            "format_issue": "#1abc9c",
            "qa_mismatch": "#e84393",
            "vague": "#9b59b6",
            "dead_link": "#e67e22",
        }
    
    def generate(self, detection_result: Dict, suggestions: List[Dict], 
                 coverage_gaps: List[Dict], entries: List[Dict]) -> str:
        """生成完整HTML报告"""
        stats = detection_result["stats"]
        results = detection_result["results"]
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>知识库质量治理报告</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ 
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif;
    background: #f5f6fa; color: #2d3436; line-height: 1.6; padding: 20px;
}}
.container {{ max-width: 1200px; margin: 0 auto; }}
.header {{ 
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
    color: white; padding: 40px; border-radius: 12px; margin-bottom: 30px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
}}
.header h1 {{ font-size: 28px; margin-bottom: 8px; }}
.header .meta {{ font-size: 14px; opacity: 0.9; }}
.summary-grid {{ 
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px;
}}
.summary-card {{ 
    background: white; padding: 24px; border-radius: 12px; text-align: center;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}}
.summary-card .number {{ font-size: 36px; font-weight: 700; margin: 8px 0; }}
.summary-card .label {{ font-size: 13px; color: #636e72; }}
.summary-card.warning .number {{ color: #e74c3c; }}
.summary-card.success .number {{ color: #00b894; }}
.summary-card.info .number {{ color: #0984e3; }}
.section {{
    background: white; border-radius: 12px; padding: 30px; margin-bottom: 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}}
.section h2 {{ font-size: 20px; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid #f0f0f0; }}
.chart-container {{ margin: 20px 0; }}
.bar-chart {{ display: flex; flex-direction: column; gap: 12px; }}
.bar-row {{ display: flex; align-items: center; gap: 12px; }}
.bar-label {{ width: 120px; font-size: 14px; text-align: right; flex-shrink: 0; }}
.bar-track {{ flex: 1; background: #f0f0f0; border-radius: 6px; height: 28px; position: relative; }}
.bar-fill {{ height: 100%; border-radius: 6px; display: flex; align-items: center; justify-content: flex-end; padding-right: 10px; color: white; font-size: 12px; font-weight: 600; transition: width 0.6s ease; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ background: #f8f9fa; padding: 12px 10px; text-align: left; font-weight: 600; border-bottom: 2px solid #dee2e6; white-space: nowrap; }}
td {{ padding: 12px 10px; border-bottom: 1px solid #f1f2f6; vertical-align: top; }}
tr:hover {{ background: #f8f9fa; }}
.badge {{ display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; white-space: nowrap; }}
.badge-critical {{ background: #ffeaa7; color: #d63031; }} 
.badge-major {{ background: #fff3cd; color: #856404; }}
.badge-minor {{ background: #d1ecf1; color: #0c5460; }}
.badge-action {{ background: #dfe6e9; color: #2d3436; }}
.priority-P0 {{ background: #e74c3c; color: white; }}
.priority-P1 {{ background: #f39c12; color: white; }}
.priority-P2 {{ background: #3498db; color: white; }}
.priority-P3 {{ background: #95a5a6; color: white; }}
.issue-detail {{ max-width: 400px; word-wrap: break-word; }}
.answer-preview {{ max-width: 300px; color: #636e72; font-size: 12px; word-wrap: break-word; }}
.suggestion-text {{ max-width: 400px; word-wrap: break-word; }}
.pie-container {{ display: flex; align-items: center; gap: 30px; flex-wrap: wrap; }}
.legend {{ display: flex; flex-direction: column; gap: 8px; }}
.legend-item {{ display: flex; align-items: center; gap: 8px; font-size: 13px; }}
.legend-dot {{ width: 12px; height: 12px; border-radius: 3px; flex-shrink: 0; }}
.toc {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 24px; }}
.toc a {{ color: #0984e3; text-decoration: none; font-size: 14px; }}
.toc a:hover {{ text-decoration: underline; }}
.toc ul {{ list-style: none; }}
.toc li {{ padding: 4px 0; }}
.footer {{ text-align: center; padding: 30px; color: #636e72; font-size: 13px; }}
@media (max-width: 768px) {{
    .summary-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .bar-label {{ width: 80px; font-size: 12px; }}
}}
</style>
</head>
<body>
<div class="container">
"""
        
        # Header
        html += self._render_header(stats)
        
        # TOC
        html += self._render_toc()
        
        # Summary cards
        html += self._render_summary_cards(stats)
        
        # Problem distribution
        html += self._render_problem_distribution(stats)
        
        # Severity distribution
        html += self._render_severity_distribution(stats)
        
        # Category distribution
        html += self._render_category_distribution(stats)
        
        # Problem entries detail
        html += self._render_problem_entries(detection_result)
        
        # Governance suggestions
        html += self._render_suggestions(suggestions)
        
        # Coverage gaps
        html += self._render_coverage_gaps(coverage_gaps)
        
        # Priority plan
        html += self._render_priority_plan(suggestions, stats)
        
        # Footer
        html += """
<div class="footer">
<p>本报告由知识库质量治理工具自动生成</p>
<p>生成时间: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
</div>
</div>
</body>
</html>"""
        
        return html
    
    def _render_header(self, stats: Dict) -> str:
        return f"""
<div class="header">
    <h1>知识库质量治理报告</h1>
    <div class="meta">
        检测时间: {datetime.now().strftime("%Y-%m-%d %H:%M")} ｜ 
        知识库总条目: {stats['total_entries']} ｜ 
        问题条目: {stats['problem_entry_count']} ｜ 
        问题总数: {stats['total_issues']}
    </div>
</div>
"""
    
    def _render_toc(self) -> str:
        return """
<div class="toc">
    <ul>
        <li><a href="#summary">一、概览摘要</a></li>
        <li><a href="#distribution">二、问题分布统计</a></li>
        <li><a href="#entries">三、问题条目明细</a></li>
        <li><a href="#suggestions">四、治理建议</a></li>
        <li><a href="#gaps">五、覆盖缺失分析</a></li>
        <li><a href="#plan">六、优先处理计划</a></li>
    </ul>
</div>
"""
    
    def _render_summary_cards(self, stats: Dict) -> str:
        health_score = round((1 - stats['problem_entry_count'] / stats['total_entries']) * 100, 1)
        return f"""
<div class="summary-grid" id="summary">
    <div class="summary-card info">
        <div class="label">知识库总条目</div>
        <div class="number">{stats['total_entries']}</div>
    </div>
    <div class="summary-card warning">
        <div class="label">问题条目数</div>
        <div class="number">{stats['problem_entry_count']}</div>
    </div>
    <div class="summary-card success">
        <div class="label">健康度评分</div>
        <div class="number">{health_score}<span style="font-size:18px">%</span></div>
    </div>
    <div class="summary-card info">
        <div class="label">检测到问题总数</div>
        <div class="number">{stats['total_issues']}</div>
    </div>
</div>
"""
    
    def _render_problem_distribution(self, stats: Dict) -> str:
        by_type = stats.get("by_type", {})
        if not by_type:
            return ""
        
        max_count = max(by_type.values()) if by_type else 1
        
        # 按数量排序
        sorted_types = sorted(by_type.items(), key=lambda x: -x[1])
        
        bars = ""
        for type_code, count in sorted_types:
            pt = ProblemType.get_by_code(type_code)
            name = pt["name"] if pt else type_code
            color = self.type_colors.get(type_code, "#95a5a6")
            width = (count / max_count) * 100 if max_count > 0 else 0
            pct = count / stats['total_issues'] * 100 if stats['total_issues'] > 0 else 0
            
            bars += f"""
            <div class="bar-row">
                <div class="bar-label">{name}</div>
                <div class="bar-track">
                    <div class="bar-fill" style="width: {width}%; background: {color};">{count} ({pct:.1f}%)</div>
                </div>
            </div>"""
        
        # 添加问题类型说明表
        type_desc = ""
        for type_code, count in sorted_types:
            pt = ProblemType.get_by_code(type_code)
            if pt:
                type_desc += f"""
                <tr>
                    <td><span class="badge" style="background: {self.type_colors.get(type_code, '#95a5a6')}20; color: {self.type_colors.get(type_code, '#2d3436')};">{pt['name']}</span></td>
                    <td>{pt['description']}</td>
                    <td><span class="badge badge-{pt['severity']}">{SEVERITY_LABEL.get(pt['severity'], pt['severity'])}</span></td>
                    <td><span class="badge badge-action">{pt['governance_action']}</span></td>
                    <td style="text-align:center; font-weight:600;">{count}</td>
                </tr>"""
        
        return f"""
<div class="section" id="distribution">
    <h2>二、问题分布统计</h2>
    
    <h3 style="font-size:16px; margin-bottom:12px;">2.1 问题类型分布</h3>
    <div class="chart-container">
        <div class="bar-chart">
            {bars}
        </div>
    </div>
    
    <h3 style="font-size:16px; margin: 24px 0 12px;">2.2 问题类型说明</h3>
    <table>
        <thead>
            <tr>
                <th>问题类型</th>
                <th>说明</th>
                <th>严重等级</th>
                <th>治理动作</th>
                <th style="text-align:center;">数量</th>
            </tr>
        </thead>
        <tbody>
            {type_desc}
        </tbody>
    </table>
</div>
"""
    
    def _render_severity_distribution(self, stats: Dict) -> str:
        by_severity = stats.get("by_severity", {})
        if not by_severity:
            return ""
        
        total = sum(by_severity.values())
        # 构建饼图（SVG）
        svg = self._render_pie_chart(by_severity, total)
        
        legend = ""
        for sev in ["critical", "major", "minor"]:
            count = by_severity.get(sev, 0)
            if count > 0:
                color = self.color_map.get(sev, "#95a5a6")
                pct = count / total * 100
                legend += f"""
                <div class="legend-item">
                    <div class="legend-dot" style="background: {color};"></div>
                    <span>{SEVERITY_LABEL.get(sev, sev)}: {count}个 ({pct:.1f}%)</span>
                </div>"""
        
        return f"""
<div class="section">
    <h3 style="font-size:16px; margin-bottom:12px;">2.3 严重等级分布</h3>
    <div class="pie-container">
        {svg}
        <div class="legend">{legend}</div>
    </div>
</div>
"""
    
    def _render_pie_chart(self, data: Dict, total: int) -> str:
        """渲染SVG饼图"""
        colors = []
        for sev in ["critical", "major", "minor"]:
            if sev in data and data[sev] > 0:
                colors.append((sev, data[sev], self.color_map.get(sev)))
        
        if not colors:
            return ""
        
        cx, cy, r = 100, 100, 80
        start_angle = -90  # 从顶部开始
        
        paths = ""
        for sev, count, color in colors:
            angle = count / total * 360
            end_angle = start_angle + angle
            
            # 计算弧线路径
            import math
            start_rad = math.radians(start_angle)
            end_rad = math.radians(end_angle)
            
            x1 = cx + r * math.cos(start_rad)
            y1 = cy + r * math.sin(start_rad)
            x2 = cx + r * math.cos(end_rad)
            y2 = cy + r * math.sin(end_rad)
            
            large_arc = 1 if angle > 180 else 0
            
            paths += f'<path d="M {cx} {cy} L {x1:.1f} {y1:.1f} A {r} {r} 0 {large_arc} 1 {x2:.1f} {y2:.1f} Z" fill="{color}" stroke="white" stroke-width="2"/>'
            
            start_angle = end_angle
        
        return f'<svg width="200" height="200" viewBox="0 0 200 200">{paths}<circle cx="100" cy="100" r="35" fill="white"/><text x="100" y="95" text-anchor="middle" font-size="24" font-weight="bold" fill="#2d3436">{total}</text><text x="100" y="115" text-anchor="middle" font-size="11" fill="#636e72">总问题数</text></svg>'
    
    def _render_category_distribution(self, stats: Dict) -> str:
        by_category = stats.get("by_category", {})
        if not by_category:
            return ""
        
        max_count = max(by_category.values()) if by_category else 1
        sorted_cats = sorted(by_category.items(), key=lambda x: -x[1])
        
        bars = ""
        for cat, count in sorted_cats:
            width = (count / max_count) * 100 if max_count > 0 else 0
            bars += f"""
            <div class="bar-row">
                <div class="bar-label">{cat}</div>
                <div class="bar-track">
                    <div class="bar-fill" style="width: {width}%; background: #6c5ce7;">{count}</div>
                </div>
            </div>"""
        
        return f"""
<div class="section">
    <h3 style="font-size:16px; margin-bottom:12px;">2.4 问题分类分布（按知识库分类）</h3>
    <div class="chart-container">
        <div class="bar-chart">
            {bars}
        </div>
    </div>
</div>
"""
    
    def _render_problem_entries(self, detection_result: Dict) -> str:
        results = detection_result["results"]
        # 按严重等级排序
        severity_order = {"critical": 0, "major": 1, "minor": 2}
        results_sorted = sorted(results, key=lambda x: (severity_order.get(x.get("severity"), 3), x.get("entry_id", "")))
        
        rows = ""
        for r in results_sorted:
            pt = ProblemType.get_by_code(r["problem_type"])
            type_name = pt["name"] if pt else r["problem_type"]
            sev = r.get("severity", "major")
            method = r.get("detection_method", "rule")
            confirmed = r.get("confirmed_by", "")
            method_badge = f'<span class="badge" style="background:#a29bfe20; color:#6c5ce7;">{method}</span>'
            if confirmed:
                method_badge += ' <span class="badge" style="background:#00b89420; color:#00b894;">双重确认</span>'
            
            rows += f"""
            <tr>
                <td><strong>{r['entry_id']}</strong></td>
                <td>{r.get('category', '')}</td>
                <td>{r['question'][:40]}{'...' if len(r['question']) > 40 else ''}</td>
                <td><span class="badge" style="background: {self.type_colors.get(r['problem_type'], '#95a5a6')}20; color: {self.type_colors.get(r['problem_type'], '#2d3436')};">{type_name}</span></td>
                <td><span class="badge badge-{sev}">{SEVERITY_LABEL.get(sev, sev)}</span></td>
                <td class="issue-detail">{r['issue_detail']}</td>
                <td>{method_badge}</td>
            </tr>"""
        
        return f"""
<div class="section" id="entries">
    <h2>三、问题条目明细</h2>
    <p style="color:#636e72; margin-bottom:16px;">共 {len(results)} 条问题记录，按严重等级排序</p>
    <div style="overflow-x: auto;">
    <table>
        <thead>
            <tr>
                <th>条目ID</th>
                <th>分类</th>
                <th>问题</th>
                <th>问题类型</th>
                <th>严重等级</th>
                <th>问题描述</th>
                <th>检测方法</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    </div>
</div>
"""
    
    def _render_suggestions(self, suggestions: List[Dict]) -> str:
        if not suggestions:
            return ""
        
        rows = ""
        for s in suggestions:
            priority = s.get("priority", 5)
            p_label = s.get("priority_label", "P2-中")
            p_class = f"priority-{p_label.split('-')[0]}"
            
            types_badges = ""
            for t in s.get("problem_types", []):
                pt = ProblemType.get_by_code(t)
                name = pt["name"] if pt else t
                types_badges += f'<span class="badge" style="background: {self.type_colors.get(t, "#95a5a6")}20; color: {self.type_colors.get(t, "#2d3436")}; margin-right:4px;">{name}</span>'
            
            rows += f"""
            <tr>
                <td><strong>{s['entry_id']}</strong></td>
                <td>{s.get('category', '')}</td>
                <td>{s['question'][:35]}{'...' if len(s.get('question', '')) > 35 else ''}</td>
                <td>{types_badges}</td>
                <td><span class="badge {p_class}">{p_label}</span></td>
                <td><span class="badge badge-action">{s['action']}</span></td>
                <td class="suggestion-text">{s['suggestion']}</td>
            </tr>"""
        
        return f"""
<div class="section" id="suggestions">
    <h2>四、治理建议</h2>
    <p style="color:#636e72; margin-bottom:16px;">共 {len(suggestions)} 条治理建议，按优先级排序</p>
    <div style="overflow-x: auto;">
    <table>
        <thead>
            <tr>
                <th>条目ID</th>
                <th>分类</th>
                <th>问题</th>
                <th>问题类型</th>
                <th>优先级</th>
                <th>治理动作</th>
                <th>具体建议</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    </div>
</div>
"""
    
    def _render_coverage_gaps(self, gaps: List[Dict]) -> str:
        if not gaps:
            return """
<div class="section" id="gaps">
    <h2>五、覆盖缺失分析</h2>
    <p style="color:#00b894;">知识库覆盖情况良好，未发现明显的主题缺失。</p>
</div>
"""
        
        rows = ""
        for g in gaps:
            sim = g.get('best_match_similarity', 0)
            rows += f"""
            <tr>
                <td>{g['category']}</td>
                <td>{g['missing_topic']}</td>
                <td style="color: {'#e74c3c' if sim < 0.2 else '#f39c12'};">{sim:.0%}</td>
                <td>{g.get('best_match_entry', '无匹配') or '无匹配'}</td>
                <td><span class="badge badge-action">{g['action']}</span></td>
                <td>{g['suggestion']}</td>
            </tr>"""
        
        return f"""
<div class="section" id="gaps">
    <h2>五、覆盖缺失分析</h2>
    <p style="color:#636e72; margin-bottom:16px;">基于电商客服核心问题清单，发现 {len(gaps)} 个潜在覆盖缺失主题</p>
    <table>
        <thead>
            <tr>
                <th>分类</th>
                <th>缺失主题</th>
                <th>最佳匹配相似度</th>
                <th>最接近条目</th>
                <th>建议动作</th>
                <th>建议</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
</div>
"""
    
    def _render_priority_plan(self, suggestions: List[Dict], stats: Dict) -> str:
        # 按优先级分组
        p0 = [s for s in suggestions if s["priority"] >= 8]
        p1 = [s for s in suggestions if 6 <= s["priority"] < 8]
        p2 = [s for s in suggestions if 4 <= s["priority"] < 6]
        p3 = [s for s in suggestions if s["priority"] < 4]
        
        # 按治理动作统计
        action_counts = {}
        for s in suggestions:
            action_counts[s["action"]] = action_counts.get(s["action"], 0) + 1
        
        action_summary = ""
        for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
            action_summary += f'<span class="badge badge-action" style="margin-right:8px; font-size:14px; padding:4px 14px;">{action}: {count}条</span>'
        
        return f"""
<div class="section" id="plan">
    <h2>六、优先处理计划</h2>
    
    <h3 style="font-size:16px; margin-bottom:12px;">6.1 治理动作汇总</h3>
    <div style="margin-bottom: 24px;">{action_summary}</div>
    
    <h3 style="font-size:16px; margin-bottom:12px;">6.2 分优先级处理建议</h3>
    <table>
        <thead>
            <tr>
                <th>优先级</th>
                <th>条目数</th>
                <th>处理建议</th>
                <th>建议时限</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><span class="badge priority-P0">P0-紧急</span></td>
                <td style="font-weight:600;">{len(p0)}</td>
                <td>包含条目矛盾、问答不匹配等严重问题，可能导致客服回复错误信息。建议立即处理。</td>
                <td>1-2个工作日</td>
            </tr>
            <tr>
                <td><span class="badge priority-P1">P1-高</span></td>
                <td style="font-weight:600;">{len(p1)}</td>
                <td>包含内容过时、回答不完整、信息模糊等问题，影响用户体验。建议本周内处理。</td>
                <td>3-5个工作日</td>
            </tr>
            <tr>
                <td><span class="badge priority-P2">P2-中</span></td>
                <td style="font-weight:600;">{len(p2)}</td>
                <td>包含格式问题等，不影响信息正确性但影响阅读体验。建议两周内处理。</td>
                <td>1-2周</td>
            </tr>
            <tr>
                <td><span class="badge priority-P3">P3-低</span></td>
                <td style="font-weight:600;">{len(p3)}</td>
                <td>包含内容重复等，建议在定期维护时合并处理。</td>
                <td>下次维护周期</td>
            </tr>
        </tbody>
    </table>
    
    <h3 style="font-size:16px; margin: 24px 0 12px;">6.3 长期治理建议</h3>
    <ul style="padding-left: 20px; line-height: 2; color: #636e72;">
        <li><strong>建立定期巡检机制</strong>：每月运行一次知识库质量检测工具，及时发现新增问题</li>
        <li><strong>制定编辑规范</strong>：统一格式、标点、链接等标准，减少格式类问题</li>
        <li><strong>设置审核流程</strong>：新增/修改条目需经审核后发布，避免矛盾和重复</li>
        <li><strong>活动类条目自动过期</strong>：对涉及促销活动的条目设置有效期，到期自动标记为待更新</li>
        <li><strong>引入用户反馈机制</strong>：收集用户对FAQ的"有用/无用"反馈，作为质量信号</li>
        <li><strong>定期补充覆盖</strong>：根据客服对话日志分析高频问题，检查知识库是否已覆盖</li>
    </ul>
</div>
"""
