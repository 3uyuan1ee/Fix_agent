"""
静态分析报告生成器
负责合并分析结果、排序问题并生成统一报告
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from ..utils.logger import get_logger
from ..utils.config import get_config_manager
from .static_coordinator import StaticAnalysisResult, AnalysisIssue, SeverityLevel


class StaticAnalysisReportGenerator:
    """静态分析报告生成器"""

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
            self.config = self.config_manager.get_section('static_analysis')
        except:
            self.config = {}
        self.report_config = self.config.get('report', {})

        # 严重程度排序权重
        self.severity_weights = {
            SeverityLevel.ERROR: 1000,
            SeverityLevel.WARNING: 100,
            SeverityLevel.INFO: 10,
            SeverityLevel.LOW: 1
        }

        self.logger.info("StaticAnalysisReportGenerator initialized")

    def merge_results(self, results: List[StaticAnalysisResult]) -> StaticAnalysisResult:
        """
        合并多个静态分析结果

        Args:
            results: 静态分析结果列表

        Returns:
            合并后的静态分析结果
        """
        if not results:
            return StaticAnalysisResult(file_path="")

        # 创建合并结果
        merged_result = StaticAnalysisResult(
            file_path="multiple_files",
            execution_time=sum(r.execution_time for r in results)
        )

        # 合并问题
        all_issues = []
        tool_results = {}

        for result in results:
            all_issues.extend(result.issues)
            tool_results.update(result.tool_results)

        merged_result.issues = all_issues
        merged_result.tool_results = tool_results

        # 生成合并摘要
        merged_result.summary = self._generate_merged_summary(results, merged_result)

        self.logger.info(f"Merged {len(results)} analysis results with {len(all_issues)} total issues")

        return merged_result

    def sort_issues(self, issues: List[AnalysisIssue]) -> List[AnalysisIssue]:
        """
        按严重程度排序问题

        Args:
            issues: 问题列表

        Returns:
            排序后的问题列表
        """
        def sort_key(issue: AnalysisIssue):
            # 主要按严重程度排序，次要按行号排序
            severity_weight = self.severity_weights.get(issue.severity, 0)
            return (-severity_weight, issue.line, issue.column)

        sorted_issues = sorted(issues, key=sort_key)

        self.logger.debug(f"Sorted {len(sorted_issues)} issues by severity")

        return sorted_issues

    def deduplicate_issues(self, issues: List[AnalysisIssue]) -> List[AnalysisIssue]:
        """
        去重问题（相同位置、相同消息的问题）

        Args:
            issues: 问题列表

        Returns:
            去重后的问题列表
        """
        seen_issues = set()
        unique_issues = []

        for issue in issues:
            # 创建唯一标识符
            issue_key = (
                issue.file_path,
                issue.line,
                issue.column,
                issue.message,
                issue.severity.value
            )

            if issue_key not in seen_issues:
                seen_issues.add(issue_key)
                unique_issues.append(issue)

        removed_count = len(issues) - len(unique_issues)
        if removed_count > 0:
            self.logger.debug(f"Removed {removed_count} duplicate issues")

        return unique_issues

    def generate_report(self, results: List[StaticAnalysisResult],
                       output_format: str = "json") -> Dict[str, Any]:
        """
        生成统一的分析报告

        Args:
            results: 静态分析结果列表
            output_format: 输出格式 (json, summary, detailed)

        Returns:
            分析报告字典
        """
        self.logger.info(f"Generating {output_format} report for {len(results)} files")

        # 合并结果
        merged_result = self.merge_results(results)

        # 去重和排序
        unique_issues = self.deduplicate_issues(merged_result.issues)
        sorted_issues = self.sort_issues(unique_issues)

        # 生成报告
        report = {
            "metadata": self._generate_report_metadata(results),
            "summary": self._generate_overall_summary(sorted_issues, results),
            "issues": [issue.to_dict() for issue in sorted_issues],
            "file_details": self._generate_file_details(results),
            "tool_details": self._generate_tool_details(results)
        }

        # 根据格式调整报告内容
        if output_format == "summary":
            # 简化格式，只包含摘要
            report = {
                "metadata": report["metadata"],
                "summary": report["summary"]
            }
        elif output_format == "detailed":
            # 详细格式，包含工具原始结果
            report["raw_results"] = {result.file_path: result.tool_results for result in results}

        self.logger.info(f"Generated {output_format} report with {len(sorted_issues)} issues")

        return report

    def save_report(self, report: Dict[str, Any], output_path: str,
                   output_format: str = "json") -> bool:
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
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
            else:
                # 生成文本格式报告
                text_report = self._generate_text_report(report)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(text_report)

            self.logger.info(f"Report saved to: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save report to {output_path}: {e}")
            return False

    def _generate_report_metadata(self, results: List[StaticAnalysisResult]) -> Dict[str, Any]:
        """生成报告元数据"""
        return {
            "generated_at": datetime.now().isoformat(),
            "total_files": len(results),
            "total_execution_time": sum(r.execution_time for r in results),
            "tools_used": list(set().union(*[list(r.tool_results.keys()) for r in results])),
            "version": "1.0.0"
        }

    def _generate_overall_summary(self, issues: List[AnalysisIssue],
                                 results: List[StaticAnalysisResult]) -> Dict[str, Any]:
        """生成总体摘要"""
        summary = {
            "total_issues": len(issues),
            "files_with_issues": len([r for r in results if r.issues]),
            "severity_distribution": {},
            "tool_distribution": {},
            "issue_types": {},
            "top_issues": []
        }

        # 统计严重程度分布
        for issue in issues:
            severity = issue.severity.value
            summary["severity_distribution"][severity] = summary["severity_distribution"].get(severity, 0) + 1

        # 统计工具分布
        for issue in issues:
            tool = issue.tool_name
            summary["tool_distribution"][tool] = summary["tool_distribution"].get(tool, 0) + 1

        # 统计问题类型
        for issue in issues:
            issue_type = issue.issue_type
            summary["issue_types"][issue_type] = summary["issue_types"].get(issue_type, 0) + 1

        # 获取前10个最严重的问题
        summary["top_issues"] = [issue.to_dict() for issue in issues[:10]]

        return summary

    def _generate_file_details(self, results: List[StaticAnalysisResult]) -> List[Dict[str, Any]]:
        """生成文件详情"""
        file_details = []

        for result in results:
            file_detail = {
                "file_path": result.file_path,
                "issue_count": len(result.issues),
                "execution_time": result.execution_time,
                "severity_distribution": result.summary.get("severity_distribution", {}),
                "tool_distribution": result.summary.get("tool_distribution", {})
            }
            file_details.append(file_detail)

        # 按问题数量排序
        file_details.sort(key=lambda x: x["issue_count"], reverse=True)

        return file_details

    def _generate_tool_details(self, results: List[StaticAnalysisResult]) -> Dict[str, Any]:
        """生成工具详情"""
        tool_stats = {}

        for result in results:
            for tool_name, tool_result in result.tool_results.items():
                if tool_name not in tool_stats:
                    tool_stats[tool_name] = {
                        "files_analyzed": 0,
                        "total_issues": 0,
                        "execution_time": 0.0
                    }

                tool_stats[tool_name]["files_analyzed"] += 1
                tool_stats[tool_name]["execution_time"] += result.execution_time

                # 根据工具类型统计问题数量
                if tool_name == 'ast':
                    tool_stats[tool_name]["total_issues"] += len(tool_result.get('errors', []))
                elif tool_name == 'pylint':
                    tool_stats[tool_name]["total_issues"] += len(tool_result.get('issues', []))
                elif tool_name == 'flake8':
                    tool_stats[tool_name]["total_issues"] += len(tool_result.get('issues', []))
                elif tool_name == 'bandit':
                    tool_stats[tool_name]["total_issues"] += len(tool_result.get('vulnerabilities', []))

        return tool_stats

    def _generate_merged_summary(self, results: List[StaticAnalysisResult],
                               merged_result: StaticAnalysisResult) -> Dict[str, Any]:
        """生成合并结果的摘要"""
        summary = {
            "total_files": len(results),
            "total_issues": len(merged_result.issues),
            "files_with_issues": len([r for r in results if r.issues]),
            "severity_distribution": {},
            "tool_distribution": {},
            "issue_types": {},
            "execution_time": merged_result.execution_time
        }

        # 统计各种分布
        for result in results:
            for severity, count in result.summary.get("severity_distribution", {}).items():
                summary["severity_distribution"][severity] = summary["severity_distribution"].get(severity, 0) + count

            for tool, count in result.summary.get("tool_distribution", {}).items():
                summary["tool_distribution"][tool] = summary["tool_distribution"].get(tool, 0) + count

            for issue_type, count in result.summary.get("issue_types", {}).items():
                summary["issue_types"][issue_type] = summary["issue_types"].get(issue_type, 0) + count

        return summary

    def _generate_text_report(self, report: Dict[str, Any]) -> str:
        """生成文本格式的报告"""
        lines = []

        # 报告标题
        lines.append("=" * 60)
        lines.append("静态分析报告")
        lines.append("=" * 60)
        lines.append("")

        # 元数据
        metadata = report["metadata"]
        lines.append(f"生成时间: {metadata['generated_at']}")
        lines.append(f"分析文件数: {metadata['total_files']}")
        lines.append(f"使用工具: {', '.join(metadata['tools_used'])}")
        lines.append(f"总执行时间: {metadata['total_execution_time']:.2f}s")
        lines.append("")

        # 摘要
        summary = report["summary"]
        lines.append("## 总体摘要")
        lines.append("-" * 30)
        lines.append(f"总问题数: {summary['total_issues']}")
        lines.append(f"有问题文件数: {summary['files_with_issues']}")

        if summary["severity_distribution"]:
            lines.append("")
            lines.append("严重程度分布:")
            for severity, count in sorted(summary["severity_distribution"].items(),
                                        key=lambda x: self.severity_weights.get(SeverityLevel(x[0]), 0),
                                        reverse=True):
                lines.append(f"  {severity}: {count}")

        if summary["tool_distribution"]:
            lines.append("")
            lines.append("工具分布:")
            for tool, count in sorted(summary["tool_distribution"].items(),
                                     key=lambda x: x[1], reverse=True):
                lines.append(f"  {tool}: {count}")

        # 文件详情
        if report.get("file_details"):
            lines.append("")
            lines.append("## 文件详情")
            lines.append("-" * 30)
            for file_detail in report["file_details"][:10]:  # 只显示前10个文件
                lines.append(f"{file_detail['file_path']}: {file_detail['issue_count']} 个问题")

        # 前10个问题
        if summary.get("top_issues"):
            lines.append("")
            lines.append("## 主要问题 (前10个)")
            lines.append("-" * 30)
            for i, issue in enumerate(summary["top_issues"][:10], 1):
                lines.append(f"{i}. [{issue['severity'].upper()}] {issue['file_path']}:{issue['line']}")
                lines.append(f"   {issue['message']}")
                lines.append(f"   工具: {issue['tool_name']}")
                lines.append("")

        return "\n".join(lines)