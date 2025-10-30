"""
静态分析结果聚合器 - T004.3
聚合多工具分析结果，为AI分析提供结构化输入
"""

import os
import hashlib
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, Counter
from datetime import datetime
import json

from ..utils.logger import get_logger
try:
    from .project_analysis_types import ProgrammingLanguage, SeverityLevel
    from .multilang_static_analyzer import StaticAnalysisResult, StaticAnalysisIssue
except ImportError:
    # 如果相关模块不可用，定义基本类型
    from enum import Enum

    class ProgrammingLanguage(Enum):
        PYTHON = "python"
        JAVASCRIPT = "javascript"
        TYPESCRIPT = "typescript"
        JAVA = "java"
        GO = "go"
        CPP = "cpp"
        CSHARP = "csharp"
        RUST = "rust"
        PHP = "php"
        RUBY = "ruby"
        SWIFT = "swift"
        KOTLIN = "kotlin"
        SCALA = "scala"
        HTML = "html"
        CSS = "css"
        JSON = "json"
        YAML = "yaml"
        XML = "xml"
        MARKDOWN = "markdown"
        SHELL = "shell"
        SQL = "sql"
        DOCKER = "docker"
        CONFIG = "config"
        OTHER = "other"

    class SeverityLevel(Enum):
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"

    @dataclass
    class StaticAnalysisIssue:
        tool_name: str
        file_path: str
        line_number: int
        column_number: Optional[int]
        severity: SeverityLevel
        message: str
        rule_id: str
        category: str
        source_code: Optional[str] = None
        end_line_number: Optional[int] = None
        confidence: Optional[str] = None

        def to_dict(self) -> Dict[str, Any]:
            return {
                "tool_name": self.tool_name,
                "file_path": self.file_path,
                "line_number": self.line_number,
                "column_number": self.column_number,
                "severity": self.severity.value,
                "message": self.message,
                "rule_id": self.rule_id,
                "category": self.category,
                "source_code": self.source_code,
                "end_line_number": self.end_line_number,
                "confidence": self.confidence
            }

    @dataclass
    class StaticAnalysisResult:
        language: ProgrammingLanguage
        tool_name: str
        issues: List[StaticAnalysisIssue] = field(default_factory=list)
        execution_time: float = 0.0
        success: bool = True
        error_message: str = ""
        execution_timestamp: str = ""


@dataclass
class AggregatedIssue:
    """聚合后的问题"""
    issue_id: str
    file_path: str
    line_number: int
    column_number: Optional[int]
    severity: SeverityLevel
    message: str
    category: str
    rule_ids: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    confidence: float = 0.0
    source_code: Optional[str] = None
    duplicate_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "issue_id": self.issue_id,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column_number": self.column_number,
            "severity": self.severity.value,
            "message": self.message,
            "category": self.category,
            "rule_ids": self.rule_ids,
            "tools": self.tools,
            "confidence": self.confidence,
            "source_code": self.source_code,
            "duplicate_count": self.duplicate_count
        }


@dataclass
class FileAnalysisSummary:
    """文件分析摘要"""
    file_path: str
    language: ProgrammingLanguage
    total_issues: int = 0
    severity_counts: Dict[str, int] = field(default_factory=dict)
    category_counts: Dict[str, int] = field(default_factory=dict)
    issue_density: float = 0.0
    complexity_score: float = 0.0
    importance_score: float = 0.0
    tools_used: List[str] = field(default_factory=list)
    analysis_timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "file_path": self.file_path,
            "language": self.language.value,
            "total_issues": self.total_issues,
            "severity_counts": self.severity_counts,
            "category_counts": self.category_counts,
            "issue_density": self.issue_density,
            "complexity_score": self.complexity_score,
            "importance_score": self.importance_score,
            "tools_used": self.tools_used,
            "analysis_timestamp": self.analysis_timestamp
        }


@dataclass
class ProjectAnalysisReport:
    """项目分析报告"""
    project_path: str
    total_files: int = 0
    total_issues: int = 0
    language_distribution: Dict[str, int] = field(default_factory=dict)
    severity_distribution: Dict[str, int] = field(default_factory=dict)
    category_distribution: Dict[str, int] = field(default_factory=dict)
    file_summaries: List[FileAnalysisSummary] = field(default_factory=list)
    aggregated_issues: List[AggregatedIssue] = field(default_factory=list)
    high_risk_files: List[str] = field(default_factory=list)
    analysis_statistics: Dict[str, Any] = field(default_factory=dict)
    analysis_timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "project_path": self.project_path,
            "total_files": self.total_files,
            "total_issues": self.total_issues,
            "language_distribution": self.language_distribution,
            "severity_distribution": self.severity_distribution,
            "category_distribution": self.category_distribution,
            "file_summaries": [summary.to_dict() for summary in self.file_summaries],
            "aggregated_issues": [issue.to_dict() for issue in self.aggregated_issues],
            "high_risk_files": self.high_risk_files,
            "analysis_statistics": self.analysis_statistics,
            "analysis_timestamp": self.analysis_timestamp
        }


class StaticAnalysisAggregator:
    """静态分析结果聚合器"""

    def __init__(self, deduplication_enabled: bool = True):
        self.deduplication_enabled = deduplication_enabled
        self.logger = get_logger()

        # 严重程度权重配置
        self.severity_weights = {
            SeverityLevel.CRITICAL: 4.0,
            SeverityLevel.HIGH: 3.0,
            SeverityLevel.MEDIUM: 2.0,
            SeverityLevel.LOW: 1.0
        }

        # 类别重要性权重
        self.category_weights = {
            "security": 1.5,
            "performance": 1.3,
            "error": 1.4,
            "warning": 1.1,
            "style": 0.8,
            "convention": 0.6,
            "refactor": 0.9
        }

    def aggregate_results(self,
                         analysis_results: Dict[str, StaticAnalysisResult],
                         project_path: str) -> ProjectAnalysisReport:
        """
        聚合多个文件的静态分析结果

        Args:
            analysis_results: 文件路径到分析结果的映射
            project_path: 项目根路径

        Returns:
            ProjectAnalysisReport: 聚合后的项目分析报告
        """
        self.logger.info(f"开始聚合静态分析结果，共 {len(analysis_results)} 个文件")

        report = ProjectAnalysisReport(
            project_path=os.path.abspath(project_path),
            analysis_timestamp=datetime.now().isoformat()
        )

        # 统计基础信息
        report.total_files = len(analysis_results)

        # 聚合每个文件的结果
        all_aggregated_issues = []
        for file_path, result in analysis_results.items():
            if result.success and result.issues:
                # 创建文件摘要
                file_summary = self._create_file_summary(file_path, result)
                report.file_summaries.append(file_summary)

                # 聚合问题
                file_aggregated_issues = self._aggregate_file_issues(result.issues)
                all_aggregated_issues.extend(file_aggregated_issues)

                # 更新统计信息
                self._update_language_distribution(report, result.language)
                self._update_tools_used(report, result.tool_name)

        # 全局去重
        if self.deduplication_enabled:
            report.aggregated_issues = self._deduplicate_issues(all_aggregated_issues)
        else:
            report.aggregated_issues = all_aggregated_issues

        # 计算全局统计
        report.total_issues = len(report.aggregated_issues)
        self._calculate_global_statistics(report)

        # 识别高风险文件
        report.high_risk_files = self._identify_high_risk_files(report.file_summaries)

        self.logger.info(
            f"静态分析结果聚合完成: {report.total_files}个文件, "
            f"{report.total_issues}个问题"
        )

        return report

    def _create_file_summary(self, file_path: str, result: StaticAnalysisResult) -> FileAnalysisSummary:
        """
        创建文件分析摘要

        Args:
            file_path: 文件路径
            result: 分析结果

        Returns:
            FileAnalysisSummary: 文件分析摘要
        """
        summary = FileAnalysisSummary(
            file_path=file_path,
            language=result.language,
            tools_used=[result.tool_name],
            analysis_timestamp=result.execution_timestamp
        )

        # 统计问题数量和严重程度分布
        severity_counts = Counter()
        category_counts = Counter()

        for issue in result.issues:
            severity_counts[issue.severity.value] += 1
            category_counts[issue.category] += 1

        summary.severity_counts = dict(severity_counts)
        summary.category_counts = dict(category_counts)
        summary.total_issues = len(result.issues)

        # 计算问题密度（每100行代码的问题数）
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)
            if line_count > 0:
                summary.issue_density = (summary.total_issues / line_count) * 100
        except Exception:
            summary.issue_density = 0.0

        # 计算复杂度分数
        summary.complexity_score = self._calculate_complexity_score(
            summary.total_issues, summary.severity_counts, summary.issue_density
        )

        # 计算重要性分数
        summary.importance_score = self._calculate_importance_score(summary)

        return summary

    def _aggregate_file_issues(self, issues: List[StaticAnalysisIssue]) -> List[AggregatedIssue]:
        """
        聚合单个文件的问题

        Args:
            issues: 问题列表

        Returns:
            List[AggregatedIssue]: 聚合后的问题列表
        """
        if not self.deduplication_enabled:
            # 如果不进行去重，直接转换
            return [self._convert_to_aggregated_issue(issue) for issue in issues]

        # 按位置分组进行去重
        position_groups = defaultdict(list)
        for issue in issues:
            position_key = (issue.file_path, issue.line_number, issue.column_number or 0)
            position_groups[position_key].append(issue)

        aggregated_issues = []
        for position_key, issues_group in position_groups.items():
            if len(issues_group) == 1:
                # 单个问题直接转换
                aggregated_issues.append(self._convert_to_aggregated_issue(issues_group[0]))
            else:
                # 多个问题需要聚合
                aggregated_issue = self._merge_issues(issues_group)
                aggregated_issues.append(aggregated_issue)

        return aggregated_issues

    def _convert_to_aggregated_issue(self, issue: StaticAnalysisIssue) -> AggregatedIssue:
        """将静态分析问题转换为聚合问题"""
        issue_id = self._generate_issue_id(issue)
        confidence = self._calculate_confidence(issue)

        return AggregatedIssue(
            issue_id=issue_id,
            file_path=issue.file_path,
            line_number=issue.line_number,
            column_number=issue.column_number,
            severity=issue.severity,
            message=issue.message,
            category=issue.category,
            rule_ids=[issue.rule_id],
            tools=[issue.tool_name],
            confidence=confidence,
            source_code=issue.source_code,
            duplicate_count=1
        )

    def _merge_issues(self, issues: List[StaticAnalysisIssue]) -> AggregatedIssue:
        """
        合并多个重复问题

        Args:
            issues: 重复的问题列表

        Returns:
            AggregatedIssue: 合并后的聚合问题
        """
        # 选择最严重的严重程度
        severities = [issue.severity for issue in issues]
        most_severe = max(severities, key=lambda s: self.severity_weights[s])

        # 合并规则ID和工具
        rule_ids = list(set(issue.rule_id for issue in issues))
        tools = list(set(issue.tool_name for issue in issues))

        # 选择第一个问题的基本信息（通常最完整）
        base_issue = issues[0]

        # 合并消息
        messages = [issue.message for issue in issues]
        merged_message = self._merge_similar_messages(messages)

        # 计算合并后的置信度
        confidence = sum(self._calculate_confidence(issue) for issue in issues) / len(issues)

        issue_id = self._generate_issue_id(base_issue)

        return AggregatedIssue(
            issue_id=issue_id,
            file_path=base_issue.file_path,
            line_number=base_issue.line_number,
            column_number=base_issue.column_number,
            severity=most_severe,
            message=merged_message,
            category=base_issue.category,
            rule_ids=rule_ids,
            tools=tools,
            confidence=confidence,
            source_code=base_issue.source_code,
            duplicate_count=len(issues)
        )

    def _deduplicate_issues(self, issues: List[AggregatedIssue]) -> List[AggregatedIssue]:
        """
        全局去重问题

        Args:
            issues: 聚合问题列表

        Returns:
            List[AggregatedIssue]: 去重后的问题列表
        """
        seen_keys = set()
        deduplicated = []

        for issue in issues:
            # 创建去重键（基于文件路径、行号、消息内容）
            dedup_key = (
                issue.file_path,
                issue.line_number,
                issue.column_number or 0,
                self._normalize_message_for_dedup(issue.message)
            )

            if dedup_key not in seen_keys:
                seen_keys.add(dedup_key)
                deduplicated.append(issue)
            else:
                # 如果发现重复，增加现有问题的重复计数
                for existing_issue in deduplicated:
                    if (
                        existing_issue.file_path == issue.file_path and
                        existing_issue.line_number == issue.line_number and
                        existing_issue.column_number == (issue.column_number or 0) and
                        self._normalize_message_for_dedup(existing_issue.message) ==
                        self._normalize_message_for_dedup(issue.message)
                    ):
                        existing_issue.duplicate_count += issue.duplicate_count
                        # 合并工具和规则ID
                        existing_issue.tools = list(set(existing_issue.tools + issue.tools))
                        existing_issue.rule_ids = list(set(existing_issue.rule_ids + issue.rule_ids))
                        break

        return deduplicated

    def _generate_issue_id(self, issue: StaticAnalysisIssue) -> str:
        """生成问题唯一ID"""
        content = f"{issue.file_path}:{issue.line_number}:{issue.rule_id}:{issue.message[:50]}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:12]

    def _calculate_confidence(self, issue: StaticAnalysisIssue) -> float:
        """计算问题置信度"""
        base_confidence = 0.8

        # 根据工具调整置信度
        tool_confidence_map = {
            "pylint": 0.9,
            "flake8": 0.85,
            "bandit": 0.8,
            "eslint": 0.85,
        }

        confidence = tool_confidence_map.get(issue.tool_name, base_confidence)

        # 根据严重程度调整
        if issue.severity == SeverityLevel.CRITICAL:
            confidence = min(confidence + 0.1, 1.0)
        elif issue.severity == SeverityLevel.LOW:
            confidence = max(confidence - 0.1, 0.5)

        return round(confidence, 2)

    def _calculate_complexity_score(self,
                                  total_issues: int,
                                  severity_counts: Dict[str, int],
                                  issue_density: float) -> float:
        """计算文件复杂度分数"""
        # 基础分数
        base_score = total_issues

        # 严重程度加权
        weighted_score = 0.0
        for severity, count in severity_counts.items():
            try:
                severity_enum = SeverityLevel(severity)
                weight = self.severity_weights.get(severity_enum, 1.0)
                weighted_score += count * weight
            except ValueError:
                weighted_score += count

        # 问题密度调整
        density_factor = min(issue_density / 10.0, 2.0)  # 限制密度因子最大为2

        final_score = (weighted_score * 0.7 + base_score * 0.3) * (1 + density_factor)

        return round(final_score, 2)

    def _calculate_importance_score(self, summary: FileAnalysisSummary) -> float:
        """计算文件重要性分数"""
        score = 0.0

        # 基于问题数量的基础分数
        score += summary.total_issues * 10

        # 基于严重程度的加权分数
        for severity, count in summary.severity_counts.items():
            try:
                severity_enum = SeverityLevel(severity)
                weight = self.severity_weights.get(severity_enum, 1.0)
                score += count * weight * 20
            except ValueError:
                score += count * 10

        # 基于问题密度的分数
        score += summary.issue_density * 5

        # 基于类别的分数（安全、性能等类别更重要）
        for category, count in summary.category_counts.items():
            category_weight = self.category_weights.get(category, 1.0)
            score += count * category_weight * 15

        return round(score, 2)

    def _update_language_distribution(self,
                                    report: ProjectAnalysisReport,
                                    language: ProgrammingLanguage) -> None:
        """更新语言分布统计"""
        lang_name = language.value
        report.language_distribution[lang_name] = report.language_distribution.get(lang_name, 0) + 1

    def _update_tools_used(self,
                          report: ProjectAnalysisReport,
                          tool_name: str) -> None:
        """更新工具使用统计"""
        # 这个方法会在分析统计中统一处理
        pass

    def _calculate_global_statistics(self, report: ProjectAnalysisReport) -> None:
        """计算全局统计信息"""
        # 严重程度分布
        severity_counts = Counter()
        category_counts = Counter()
        tool_usage = Counter()

        for issue in report.aggregated_issues:
            severity_counts[issue.severity.value] += 1
            category_counts[issue.category] += 1
            for tool in issue.tools:
                tool_usage[tool] += 1

        report.severity_distribution = dict(severity_counts)
        report.category_distribution = dict(category_counts)

        # 分析统计
        avg_issues_per_file = report.total_issues / report.total_files if report.total_files > 0 else 0
        high_severity_ratio = (
            severity_counts.get('critical', 0) + severity_counts.get('high', 0)
        ) / report.total_issues if report.total_issues > 0 else 0

        report.analysis_statistics = {
            "avg_issues_per_file": round(avg_issues_per_file, 2),
            "high_severity_ratio": round(high_severity_ratio, 2),
            "most_common_category": max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else "",
            "most_used_tool": max(tool_usage.items(), key=lambda x: x[1])[0] if tool_usage else "",
            "tool_usage": dict(tool_usage),
            "files_with_issues": len([s for s in report.file_summaries if s.total_issues > 0]),
            "files_without_issues": len([s for s in report.file_summaries if s.total_issues == 0])
        }

    def _identify_high_risk_files(self,
                                file_summaries: List[FileAnalysisSummary]) -> List[str]:
        """识别高风险文件"""
        # 按重要性分数排序，取前20%作为高风险文件
        if not file_summaries:
            return []

        sorted_summaries = sorted(file_summaries, key=lambda x: x.importance_score, reverse=True)
        high_risk_count = max(1, len(sorted_summaries) // 5)

        return [summary.file_path for summary in sorted_summaries[:high_risk_count]]

    def _normalize_message_for_dedup(self, message: str) -> str:
        """标准化消息用于去重"""
        # 移除变量名、数字等变化内容，保留核心描述
        import re
        normalized = re.sub(r'\b\d+\b', '<NUM>', message)  # 替换数字
        normalized = re.sub(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', '<VAR>', normalized)  # 替换变量名
        normalized = re.sub(r'[\'""][^\'""]*[\'""]', '<STR>', normalized)  # 替换字符串
        return normalized.strip().lower()

    def _merge_similar_messages(self, messages: List[str]) -> str:
        """合并相似的消息"""
        if len(messages) == 1:
            return messages[0]

        # 选择最长的消息作为基础
        base_message = max(messages, key=len)

        # 如果消息来自不同工具，添加工具信息
        if len(set(messages)) > 1:
            return f"{base_message} (Multiple tools detected similar issues)"

        return base_message

    def generate_ai_input_data(self, report: ProjectAnalysisReport) -> Dict[str, Any]:
        """
        生成AI分析输入数据

        Args:
            report: 项目分析报告

        Returns:
            Dict[str, Any]: AI分析输入数据
        """
        # 限制问题数量以控制token使用
        max_issues = 100
        issues_for_ai = report.aggregated_issues[:max_issues]

        # 按重要性排序文件摘要
        file_summaries_for_ai = sorted(
            report.file_summaries,
            key=lambda x: x.importance_score,
            reverse=True
        )[:50]  # 限制文件数量

        ai_input = {
            "project_overview": {
                "project_path": report.project_path,
                "total_files": report.total_files,
                "total_issues": report.total_issues,
                "main_languages": dict(
                    sorted(report.language_distribution.items(),
                          key=lambda x: x[1], reverse=True)[:5]
                ),
                "analysis_summary": {
                    "avg_issues_per_file": report.analysis_statistics.get("avg_issues_per_file", 0),
                    "high_severity_ratio": report.analysis_statistics.get("high_severity_ratio", 0),
                    "most_common_category": report.analysis_statistics.get("most_common_category", "")
                }
            },
            "high_risk_files": report.high_risk_files[:10],  # 限制高风险文件数量
            "file_summaries": [summary.to_dict() for summary in file_summaries_for_ai],
            "critical_issues": [
                issue.to_dict() for issue in issues_for_ai
                if issue.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]
            ][:50],  # 限制严重问题数量
            "sample_issues": [issue.to_dict() for issue in issues_for_ai[:20]]  # 示例问题
        }

        return ai_input


# 便捷函数
def aggregate_static_analysis_results(analysis_results: Dict[str, StaticAnalysisResult],
                                    project_path: str,
                                    deduplication_enabled: bool = True) -> Dict[str, Any]:
    """
    便捷的静态分析结果聚合函数

    Args:
        analysis_results: 文件路径到分析结果的映射
        project_path: 项目根路径
        deduplication_enabled: 是否启用去重

    Returns:
        Dict[str, Any]: 聚合结果和AI输入数据
    """
    aggregator = StaticAnalysisAggregator(deduplication_enabled)
    report = aggregator.aggregate_results(analysis_results, project_path)
    ai_input = aggregator.generate_ai_input_data(report)

    return {
        "report": report.to_dict(),
        "ai_input": ai_input
    }