"""
简化版可视化工具

不依赖matplotlib等外部库，提供基础的文本报告功能。
"""

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .metrics_simple import calculate_basic_metrics


@dataclass
class EvaluationVisualizer:
    """简化版可视化器"""

    def __init__(self, results: List[Any] = None):
        """初始化简化版可视化器"""
        self.results = results or []

    def generate_comprehensive_report(self, output_dir: str):
        """生成综合可视化报告"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        print(f"[可视化] 生成报告到: {output_path}")

        # 生成文本报告
        text_report = self._generate_text_report()
        text_file = output_path / "evaluation_report.txt"
        with open(text_file, "w", encoding="utf-8") as f:
            f.write(text_report)
        print(f"[可视化] 文本报告已生成: {text_file}")

        # 生成JSON报告
        if self.results:
            metrics = calculate_basic_metrics(self.results)
            json_file = output_path / "metrics.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)
            print(f"[可视化] JSON指标已保存: {json_file}")

        # 生成HTML报告（简化版）
        html_report = self._generate_html_report()
        html_file = output_path / "report.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_report)
        print(f"[可视化] HTML报告已生成: {html_file}")

    def _generate_text_report(self) -> str:
        """生成文本格式报告"""
        if not self.results:
            return "没有评估结果可分析"

        metrics = calculate_basic_metrics(self.results)

        report_lines = [
            "Fix Agent 评估报告",
            "=" * 50,
            f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "评估摘要:",
            f"  总任务数: {metrics.get('total_tasks', 0)}",
            f"  成功任务数: {metrics.get('successful_tasks', 0)}",
            f"  失败任务数: {metrics.get('failed_tasks', 0)}",
            f"  成功率: {metrics.get('success_rate', 0):.2%}",
            f"  失败率: {metrics.get('failure_rate', 0):.2%}",
            "",
            "执行时间分析:",
            f"  平均执行时间: {metrics.get('average_execution_time', 0):.2f}秒",
            f"  中位数执行时间: {metrics.get('median_execution_time', 0):.2f}秒",
            f"  最短执行时间: {metrics.get('min_execution_time', 0):.2f}秒",
            f"  最长执行时间: {metrics.get('max_execution_time', 0):.2f}秒",
            f"  每小时处理任务数: {metrics.get('tasks_per_hour', 0):.1f}",
            "",
            "任务状态分布:",
            self._analyze_task_distribution(),
            "",
            "建议和改进:",
            self._generate_suggestions(),
            "",
            "=" * 50,
        ]

        return "\n".join(report_lines)

    def _analyze_task_distribution(self) -> str:
        """分析任务状态分布"""
        if not self.results:
            return "  无数据可分析"

        success_count = sum(
            1 for r in self.results if isinstance(r, dict) and r.get("success", False)
        )
        fail_count = len(self.results) - success_count

        lines = [
            f"  成功任务: {success_count} ({success_count/len(self.results):.1%})",
            f"  失败任务: {fail_count} ({fail_count/len(self.results):.1%})",
        ]

        # 分析错误类型
        error_types = {}
        for result in self.results:
            if isinstance(result, dict) and not result.get("success", False):
                error = result.get("error", "未知错误")
                error_types[error] = error_types.get(error, 0) + 1

        if error_types:
            lines.append("\n  错误类型分布:")
            for error, count in sorted(
                error_types.items(), key=lambda x: x[1], reverse=True
            )[:5]:
                lines.append(f"    - {error}: {count}次")

        return "\n".join(lines)

    def _generate_suggestions(self) -> str:
        """生成改进建议"""
        metrics = calculate_basic_metrics(self.results)
        success_rate = metrics.get("success_rate", 0)
        avg_time = metrics.get("average_execution_time", 0)

        suggestions = []

        if success_rate < 0.3:
            suggestions.append("- 成功率较低，建议检查agent的核心逻辑")
        elif success_rate < 0.7:
            suggestions.append("- 成功率中等，建议优化缺陷检测和修复算法")
        elif success_rate < 0.9:
            suggestions.append("- 成功率较高，建议处理边界情况")

        if avg_time > 120:
            suggestions.append("- 执行时间较长，建议优化算法复杂度")
        elif avg_time > 60:
            suggestions.append("- 执行时间偏长，建议考虑缓存优化")

        if not suggestions:
            suggestions.append("- 评估结果良好，可以考虑扩展功能")
            suggestions.append("- 尝试更大的样本量以获得更准确的评估")

        return "\n".join(f"  {s}" for s in suggestions)

    def _generate_html_report(self) -> str:
        """生成HTML格式报告"""
        if not self.results:
            return """
            <!DOCTYPE html>
            <html>
            <head><title>Fix Agent 评估报告</title></head>
            <body>
                <h1>Fix Agent 评估报告</h1>
                <p>没有评估结果可分析</p>
            </body>
            </html>
            """

        metrics = calculate_basic_metrics(self.results)

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Fix Agent 评估报告</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ text-align: center; color: #333; }}
                .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .metric {{ margin: 10px 0; }}
                .success {{ color: #28a745; }}
                .error {{ color: #dc3545; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Fix Agent 评估报告</h1>
                <p>生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>

            <div class="summary">
                <h2>评估摘要</h2>
                <div class="metric">
                    <strong>总任务数:</strong> {metrics.get('total_tasks', 0)}
                </div>
                <div class="metric">
                    <strong>成功任务数:</strong> {metrics.get('successful_tasks', 0)}
                </div>
                <div class="metric">
                    <strong>失败任务数:</strong> {metrics.get('failed_tasks', 0)}
                </div>
                <div class="metric">
                    <strong>成功率:</strong> <span class="{'success' if metrics.get('success_rate', 0) > 0.5 else 'error'}">{metrics.get('success_rate', 0):.2%}</span>
                </div>
            </div>

            <h2>执行时间分析</h2>
            <table>
                <tr><th>指标</th><th>数值</th></tr>
                <tr><td>平均执行时间</td><td>{metrics.get('average_execution_time', 0):.2f}秒</td></tr>
                <tr><td>最短执行时间</td><td>{metrics.get('min_execution_time', 0):.2f}秒</td></tr>
                <tr><td>最长执行时间</td><td>{metrics.get('max_execution_time', 0):.2f}秒</td></tr>
                <tr><td>每小时处理任务数</td><td>{metrics.get('tasks_per_hour', 0):.1f}</td></tr>
            </table>

            <div class="summary">
                <h2>改进建议</h2>
                <p>{self._generate_suggestions().replace('\n', '<br>')}</p>
            </div>

        </body>
        </html>
        """

        return html_content
