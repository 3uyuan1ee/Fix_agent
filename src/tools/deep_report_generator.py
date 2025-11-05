"""
深度分析报告生成器
负责格式化和展示深度分析结果
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.config import get_config_manager
from ..utils.logger import get_logger
from .deep_analyzer import DeepAnalysisResult


class DeepAnalysisReportGenerator:
    """深度分析报告生成器"""

    def __init__(self, config_manager=None):
        """
        初始化报告生成器

        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()

        # 获取配置
        try:
            self.config = self.config_manager.get_section("deep_analysis")
        except:
            self.config = {}
        self.report_config = self.config.get("report", {})

        self.logger.info("DeepAnalysisReportGenerator initialized")

    def generate_report(
        self, results: List[DeepAnalysisResult], output_format: str = "json"
    ) -> Dict[str, Any]:
        """
        生成深度分析报告

        Args:
            results: 深度分析结果列表
            output_format: 输出格式 (json, summary, detailed)

        Returns:
            分析报告字典
        """
        self.logger.info(
            f"Generating {output_format} deep analysis report for {len(results)} files"
        )

        # 生成报告
        report = {
            "metadata": self._generate_report_metadata(results),
            "summary": self._generate_overall_summary(results),
            "file_results": [self._process_file_result(result) for result in results],
            "analysis_insights": self._generate_analysis_insights(results),
            "recommendations": self._generate_recommendations(results),
        }

        # 根据格式调整报告内容
        if output_format == "summary":
            # 简化格式，只包含摘要和洞察
            report = {
                "metadata": report["metadata"],
                "summary": report["summary"],
                "analysis_insights": report["analysis_insights"],
                "recommendations": report["recommendations"],
            }
        elif output_format == "detailed":
            # 详细格式，包含原始结果
            report["raw_results"] = [result.to_dict() for result in results]

        self.logger.info(f"Generated {output_format} deep analysis report")

        return report

    def save_report(
        self, report: Dict[str, Any], output_path: str, output_format: str = "json"
    ) -> bool:
        """
        保存报告到文件

        Args:
            report: 分析报告
            output_path: 输出文件路径
            output_format: 输出格式

        Returns:
            是否保存成功
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if output_format == "json":
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
            else:
                # 生成文本格式报告
                text_report = self._generate_text_report(report)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(text_report)

            self.logger.info(f"Deep analysis report saved to: {output_path}")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to save deep analysis report to {output_path}: {e}"
            )
            return False

    def _process_file_result(self, result: DeepAnalysisResult) -> Dict[str, Any]:
        """处理单个文件结果"""
        file_result = {
            "file_path": result.file_path,
            "analysis_type": result.analysis_type,
            "success": result.success,
            "execution_time": result.execution_time,
            "model_used": result.model_used,
            "token_usage": result.token_usage,
            "content_summary": "",
            "key_findings": [],
            "issues_found": [],
            "recommendations": [],
        }

        if result.success and result.content:
            # 生成内容摘要
            content_lines = result.content.split("\n")
            if len(content_lines) > 10:
                file_result["content_summary"] = (
                    "\n".join(content_lines[:5])
                    + f"\n\n... (总长度: {len(content_lines)} 行)"
                )
            else:
                file_result["content_summary"] = result.content

            # 提取结构化分析结果
            if result.structured_analysis:
                structured = result.structured_analysis

                # 提取关键发现
                if "findings" in structured:
                    file_result["key_findings"] = structured["findings"][
                        :5
                    ]  # 前5个发现

                # 提取问题
                if "issues" in structured:
                    file_result["issues_found"] = structured["issues"]

                # 提取建议
                if "recommendations" in structured:
                    file_result["recommendations"] = structured["recommendations"][
                        :3
                    ]  # 前3个建议

                # 提取总体评分
                if "overall_score" in structured:
                    file_result["overall_score"] = structured["overall_score"]

                # 提取风险等级
                if "risk_level" in structured:
                    file_result["risk_level"] = structured["risk_level"]

        # 添加错误信息
        if result.error:
            file_result["error"] = result.error

        return file_result

    def _generate_report_metadata(
        self, results: List[DeepAnalysisResult]
    ) -> Dict[str, Any]:
        """生成报告元数据"""
        return {
            "generated_at": datetime.now().isoformat(),
            "total_files": len(results),
            "successful_files": len([r for r in results if r.success]),
            "total_execution_time": sum(r.execution_time for r in results),
            "models_used": list(set(r.model_used for r in results if r.model_used)),
            "analysis_types": list(set(r.analysis_type for r in results)),
            "version": "1.0.0",
        }

    def _generate_overall_summary(
        self, results: List[DeepAnalysisResult]
    ) -> Dict[str, Any]:
        """生成总体摘要"""
        successful_results = [r for r in results if r.success]

        summary = {
            "total_files": len(results),
            "successful_files": len(successful_results),
            "failed_files": len(results) - len(successful_results),
            "success_rate": len(successful_results) / len(results) if results else 0,
            "total_execution_time": sum(r.execution_time for r in results),
            "average_execution_time": (
                sum(r.execution_time for r in results) / len(results) if results else 0
            ),
            "analysis_type_distribution": {},
            "model_distribution": {},
            "token_usage_stats": {},
            "overall_assessment": {},
        }

        # 统计分析类型分布
        for result in results:
            analysis_type = result.analysis_type
            summary["analysis_type_distribution"][analysis_type] = (
                summary["analysis_type_distribution"].get(analysis_type, 0) + 1
            )

        # 统计模型分布
        for result in results:
            model = result.model_used or "unknown"
            summary["model_distribution"][model] = (
                summary["model_distribution"].get(model, 0) + 1
            )

        # 统计token使用
        total_tokens = sum(
            r.token_usage.get("total_tokens", 0) for r in successful_results
        )
        total_prompt_tokens = sum(
            r.token_usage.get("prompt_tokens", 0) for r in successful_results
        )
        total_completion_tokens = sum(
            r.token_usage.get("completion_tokens", 0) for r in successful_results
        )

        summary["token_usage_stats"] = {
            "total_tokens": total_tokens,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "average_tokens_per_file": (
                total_tokens / len(successful_results) if successful_results else 0
            ),
        }

        # 总体评估
        if successful_results:
            # 提取关键指标
            high_risk_files = 0
            total_issues = 0
            scores = []

            for result in successful_results:
                processed = self._process_file_result(result)
                if "risk_level" in processed:
                    if processed["risk_level"] in ["high", "critical"]:
                        high_risk_files += 1
                total_issues += len(processed["issues_found"])
                if "overall_score" in processed:
                    scores.append(processed["overall_score"])

            summary["overall_assessment"] = {
                "high_risk_files": high_risk_files,
                "total_issues_found": total_issues,
                "average_score": sum(scores) / len(scores) if scores else 0,
                "files_with_scores": len(scores),
                "risk_level": self._calculate_overall_risk_level(
                    high_risk_files, len(successful_results)
                ),
            }

        return summary

    def _generate_analysis_insights(
        self, results: List[DeepAnalysisResult]
    ) -> Dict[str, Any]:
        """生成分析洞察"""
        successful_results = [r for r in results if r.success]

        insights = {
            "common_issues": [],
            "best_practices": [],
            "security_concerns": [],
            "performance_insights": [],
            "architecture_patterns": [],
        }

        # 收集所有发现的问题
        all_issues = []
        all_recommendations = []

        for result in successful_results:
            processed = self._process_file_result(result)
            all_issues.extend(processed["issues_found"])
            all_recommendations.extend(processed["recommendations"])

        # 分析常见问题
        issue_counts = {}
        for issue in all_issues:
            if isinstance(issue, dict) and "type" in issue:
                issue_type = issue["type"]
                issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
            elif isinstance(issue, str):
                # 简单字符串，尝试提取关键词
                issue_lower = issue.lower()
                if "security" in issue_lower:
                    insights["security_concerns"].append(issue)
                elif "performance" in issue_lower:
                    insights["performance_insights"].append(issue)
                elif "architecture" in issue_lower:
                    insights["architecture_patterns"].append(issue)

        # 找出最常见的问题类型
        sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        insights["common_issues"] = [
            {"type": issue_type, "count": count}
            for issue_type, count in sorted_issues[:5]
        ]

        # 分析最佳实践建议
        recommendation_counts = {}
        for rec in all_recommendations:
            if isinstance(rec, dict) and "category" in rec:
                category = rec["category"]
                recommendation_counts[category] = (
                    recommendation_counts.get(category, 0) + 1
                )
            elif isinstance(rec, str):
                # 简单字符串，尝试分类
                rec_lower = rec.lower()
                if "security" in rec_lower:
                    insights["security_concerns"].append(rec)
                elif "performance" in rec_lower:
                    insights["performance_insights"].append(rec)
                elif "design" in rec_lower or "architecture" in rec_lower:
                    insights["architecture_patterns"].append(rec)

        insights["best_practices"] = [
            {"category": category, "count": count}
            for category, count in sorted(
                recommendation_counts.items(), key=lambda x: x[1], reverse=True
            )[:5]
        ]

        return insights

    def _generate_recommendations(
        self, results: List[DeepAnalysisResult]
    ) -> Dict[str, Any]:
        """生成建议"""
        successful_results = [r for r in results if r.success]

        recommendations = {
            "immediate_actions": [],
            "short_term_improvements": [],
            "long_term_refactoring": [],
            "security_improvements": [],
            "performance_optimizations": [],
        }

        # 收集所有建议
        all_recommendations = []
        for result in successful_results:
            processed = self._process_file_result(result)
            all_recommendations.extend(processed["recommendations"])

        # 按优先级和类别分类建议
        for rec in all_recommendations:
            if isinstance(rec, dict):
                priority = rec.get("priority", "medium")
                category = rec.get("category", "general")

                if priority == "high" or category == "security":
                    recommendations["immediate_actions"].append(rec)
                elif priority == "medium":
                    recommendations["short_term_improvements"].append(rec)
                elif priority == "low" or category == "architecture":
                    recommendations["long_term_refactoring"].append(rec)

                if category == "security":
                    recommendations["security_improvements"].append(rec)
                elif category == "performance":
                    recommendations["performance_optimizations"].append(rec)
            else:
                # 简单字符串，添加到默认类别
                rec_lower = rec.lower()
                if any(
                    keyword in rec_lower
                    for keyword in ["urgent", "critical", "immediate"]
                ):
                    recommendations["immediate_actions"].append(rec)
                elif "security" in rec_lower:
                    recommendations["security_improvements"].append(rec)
                elif "performance" in rec_lower:
                    recommendations["performance_optimizations"].append(rec)
                else:
                    recommendations["short_term_improvements"].append(rec)

        return recommendations

    def _calculate_overall_risk_level(
        self, high_risk_files: int, total_files: int
    ) -> str:
        """计算总体风险等级"""
        if total_files == 0:
            return "unknown"

        risk_ratio = high_risk_files / total_files

        if risk_ratio >= 0.5:
            return "critical"
        elif risk_ratio >= 0.3:
            return "high"
        elif risk_ratio >= 0.1:
            return "medium"
        else:
            return "low"

    def _generate_text_report(self, report: Dict[str, Any]) -> str:
        """生成文本格式的报告"""
        lines = []

        # 报告标题
        lines.append("=" * 70)
        lines.append("深度分析报告")
        lines.append("=" * 70)
        lines.append("")

        # 元数据
        metadata = report["metadata"]
        lines.append(f"生成时间: {metadata['generated_at']}")
        lines.append(f"分析文件数: {metadata['total_files']}")
        lines.append(f"成功文件数: {metadata['successful_files']}")
        lines.append(f"使用模型: {', '.join(metadata['models_used'])}")
        lines.append(f"分析类型: {', '.join(metadata['analysis_types'])}")
        lines.append(f"总执行时间: {metadata['total_execution_time']:.2f}s")
        lines.append("")

        # 摘要
        summary = report["summary"]
        lines.append("## 总体摘要")
        lines.append("-" * 40)
        lines.append(f"成功率: {summary['success_rate']:.1%}")
        lines.append(f"平均执行时间: {summary['average_execution_time']:.2f}s")
        lines.append(f"总token使用: {summary['token_usage_stats']['total_tokens']}")

        if summary.get("overall_assessment"):
            assessment = summary["overall_assessment"]
            lines.append(f"高风险文件数: {assessment['high_risk_files']}")
            lines.append(f"发现问题总数: {assessment['total_issues_found']}")
            lines.append(f"风险等级: {assessment['risk_level']}")

        if summary["analysis_type_distribution"]:
            lines.append("")
            lines.append("分析类型分布:")
            for analysis_type, count in sorted(
                summary["analysis_type_distribution"].items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                lines.append(f"  {analysis_type}: {count}")

        # 分析洞察
        if report.get("analysis_insights"):
            lines.append("")
            lines.append("## 分析洞察")
            lines.append("-" * 40)

            insights = report["analysis_insights"]

            if insights.get("common_issues"):
                lines.append("常见问题:")
                for issue in insights["common_issues"][:5]:
                    lines.append(f"  • {issue['type']}: {issue['count']} 次")

            if insights.get("security_concerns"):
                lines.append("")
                lines.append("安全关注点:")
                for concern in insights["security_concerns"][:3]:
                    lines.append(f"  • {concern}")

        # 建议
        if report.get("recommendations"):
            lines.append("")
            lines.append("## 改进建议")
            lines.append("-" * 40)

            recommendations = report["recommendations"]

            if recommendations.get("immediate_actions"):
                lines.append("立即行动项:")
                for action in recommendations["immediate_actions"][:3]:
                    if isinstance(action, dict):
                        lines.append(f"  • {action.get('description', str(action))}")
                    else:
                        lines.append(f"  • {action}")

            if recommendations.get("security_improvements"):
                lines.append("")
                lines.append("安全改进:")
                for improvement in recommendations["security_improvements"][:3]:
                    if isinstance(improvement, dict):
                        lines.append(
                            f"  • {improvement.get('description', str(improvement))}"
                        )
                    else:
                        lines.append(f"  • {improvement}")

        # 文件详情
        if report.get("file_results"):
            lines.append("")
            lines.append("## 文件详情")
            lines.append("-" * 40)

            for file_result in report["file_results"][:10]:  # 只显示前10个文件
                status = "✅" if file_result["success"] else "❌"
                lines.append(f"{status} {file_result['file_path']}")
                if file_result.get("risk_level"):
                    lines.append(f"   风险等级: {file_result['risk_level']}")
                if file_result.get("overall_score"):
                    lines.append(f"   评分: {file_result['overall_score']}")
                lines.append(f"   执行时间: {file_result['execution_time']:.2f}s")

        return "\n".join(lines)
