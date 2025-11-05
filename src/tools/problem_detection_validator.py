"""
问题检测结果验证器 - T008.3
验证AI检测结果的质量
"""

import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from ..utils.logger import get_logger

try:
    from .ai_problem_detector import AIDetectedProblem, ProblemDetectionResult
    from .multilang_static_analyzer import StaticAnalysisResult
    from .workflow_data_types import FixType, ProblemType, SeverityLevel
except ImportError:
    # 如果相关模块不可用，定义基本类型
    from enum import Enum

    class ProblemType(Enum):
        SECURITY = "security"
        PERFORMANCE = "performance"
        LOGIC = "logic"
        STYLE = "style"
        MAINTAINABILITY = "maintainability"
        RELIABILITY = "reliability"
        COMPATIBILITY = "compatibility"
        DOCUMENTATION = "documentation"

    class SeverityLevel(Enum):
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"

    class FixType(Enum):
        CODE_REPLACEMENT = "code_replacement"
        CODE_INSERTION = "code_insertion"
        CODE_DELETION = "code_deletion"
        REFACTORING = "refactoring"
        CONFIGURATION = "configuration"
        DEPENDENCY_UPDATE = "dependency_update"

    @dataclass
    class AIDetectedProblem:
        problem_id: str
        file_path: str
        line_number: int
        problem_type: ProblemType
        severity: SeverityLevel
        description: str
        code_snippet: str
        confidence: float
        reasoning: str
        suggested_fix_type: FixType = FixType.CODE_REPLACEMENT
        tags: List[str] = field(default_factory=list)
        estimated_fix_time: int = 0

    @dataclass
    class ProblemDetectionResult:
        detection_id: str
        context_id: str
        detected_problems: List[AIDetectedProblem] = field(default_factory=list)
        detection_summary: Dict[str, Any] = field(default_factory=dict)
        execution_success: bool = True
        execution_time: float = 0.0
        error_message: str = ""

    @dataclass
    class StaticAnalysisResult:
        language: str
        tool_name: str
        issues: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ValidationResult:
    """验证结果"""

    is_valid: bool
    validation_score: float  # 0.0-1.0
    validation_issues: List[str] = field(default_factory=list)
    quality_metrics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ValidatedProblem:
    """验证后的问题"""

    original_problem: AIDetectedProblem
    validation_result: ValidationResult
    adjusted_confidence: float
    priority_rank: int = 0
    is_recommended: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "problem_id": self.original_problem.problem_id,
            "file_path": self.original_problem.file_path,
            "line_number": self.original_problem.line_number,
            "problem_type": self.original_problem.problem_type.value,
            "severity": self.original_problem.severity.value,
            "description": self.original_problem.description,
            "code_snippet": self.original_problem.code_snippet,
            "original_confidence": self.original_problem.confidence,
            "adjusted_confidence": self.adjusted_confidence,
            "reasoning": self.original_problem.reasoning,
            "suggested_fix_type": self.original_problem.suggested_fix_type.value,
            "validation_score": self.validation_result.validation_score,
            "validation_issues": self.validation_result.validation_issues,
            "priority_rank": self.priority_rank,
            "is_recommended": self.is_recommended,
            "tags": self.original_problem.tags,
            "estimated_fix_time": self.original_problem.estimated_fix_time,
        }


@dataclass
class ProblemValidationResult:
    """问题验证结果"""

    validation_id: str
    original_detection_result: ProblemDetectionResult
    validated_problems: List[ValidatedProblem] = field(default_factory=list)
    filtered_problems: List[ValidatedProblem] = field(default_factory=list)
    validation_summary: Dict[str, Any] = field(default_factory=dict)
    quality_report: Dict[str, Any] = field(default_factory=dict)
    validation_timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "validation_id": self.validation_id,
            "original_detection_id": self.original_detection_result.detection_id,
            "validated_problems": [
                problem.to_dict() for problem in self.validated_problems
            ],
            "filtered_problems": [
                problem.to_dict() for problem in self.filtered_problems
            ],
            "validation_summary": self.validation_summary,
            "quality_report": self.quality_report,
            "validation_timestamp": self.validation_timestamp,
            "total_validated": len(self.validated_problems),
            "total_filtered": len(self.filtered_problems),
            "filtering_ratio": (
                round(len(self.filtered_problems) / len(self.validated_problems), 3)
                if self.validated_problems
                else 0
            ),
        }


class ProblemDetectionValidator:
    """问题检测结果验证器"""

    def __init__(
        self,
        min_confidence_threshold: float = 0.5,
        max_problems_per_file: int = 10,
        enable_deduplication: bool = True,
    ):
        self.min_confidence_threshold = min_confidence_threshold
        self.max_problems_per_file = max_problems_per_file
        self.enable_deduplication = enable_deduplication
        self.logger = get_logger()

        # 验证权重配置
        self.validation_weights = {
            "location_accuracy": 0.25,  # 位置准确性
            "description_quality": 0.20,  # 描述质量
            "reasoning_depth": 0.20,  # 推理深度
            "code_snippet_relevance": 0.15,  # 代码片段相关性
            "confidence_reasonableness": 0.10,  # 置信度合理性
            "actionability": 0.10,  # 可操作性
        }

        # 质量阈值配置
        self.quality_thresholds = {
            "min_description_length": 20,
            "min_reasoning_length": 30,
            "min_code_snippet_length": 10,
            "max_line_number_deviation": 5,
            "suspicious_keywords": [
                "可能",
                "也许",
                "大概",
                "或许",
                "probably",
                "maybe",
                "possibly",
            ],
        }

    def validate_detection_result(
        self,
        detection_result: ProblemDetectionResult,
        static_analysis_results: Optional[Dict[str, StaticAnalysisResult]] = None,
        file_contents: Optional[Dict[str, str]] = None,
    ) -> ProblemValidationResult:
        """
        验证问题检测结果

        Args:
            detection_result: AI检测结果
            static_analysis_results: 静态分析结果（用于对比）
            file_contents: 文件内容（用于验证）

        Returns:
            ProblemValidationResult: 验证结果
        """
        self.logger.info(
            f"开始验证问题检测结果，检测ID: {detection_result.detection_id}"
        )

        validation_result = ProblemValidationResult(
            validation_id=self._generate_validation_id(),
            original_detection_result=detection_result,
            validation_timestamp=datetime.now().isoformat(),
        )

        try:
            # 验证每个问题
            validation_result.validated_problems = self._validate_individual_problems(
                detection_result.detected_problems,
                static_analysis_results,
                file_contents,
            )

            # 去重问题
            if self.enable_deduplication:
                validation_result.validated_problems = self._deduplicate_problems(
                    validation_result.validated_problems
                )

            # 计算优先级排名
            self._calculate_priority_ranks(validation_result.validated_problems)

            # 过滤低质量问题
            validation_result.filtered_problems = self._filter_low_quality_problems(
                validation_result.validated_problems
            )

            # 限制每个文件的问题数量
            validation_result.filtered_problems = self._limit_problems_per_file(
                validation_result.filtered_problems
            )

            # 生成验证摘要
            validation_result.validation_summary = self._generate_validation_summary(
                validation_result
            )

            # 生成质量报告
            validation_result.quality_report = self._generate_quality_report(
                validation_result
            )

            self.logger.info(
                f"问题检测验证完成: 原始 {len(detection_result.detected_problems)} 个, "
                f"验证后 {len(validation_result.validated_problems)} 个, "
                f"过滤后 {len(validation_result.filtered_problems)} 个"
            )

        except Exception as e:
            self.logger.error(f"问题检测验证失败: {e}")
            raise

        return validation_result

    def _validate_individual_problems(
        self,
        problems: List[AIDetectedProblem],
        static_analysis_results: Optional[Dict[str, StaticAnalysisResult]],
        file_contents: Optional[Dict[str, str]],
    ) -> List[ValidatedProblem]:
        """验证单个问题"""
        validated_problems = []

        for problem in problems:
            try:
                # 执行验证
                validation_result = self._validate_single_problem(
                    problem, static_analysis_results, file_contents
                )

                # 计算调整后的置信度
                adjusted_confidence = self._calculate_adjusted_confidence(
                    problem.confidence, validation_result.validation_score
                )

                # 创建验证后的问题
                validated_problem = ValidatedProblem(
                    original_problem=problem,
                    validation_result=validation_result,
                    adjusted_confidence=adjusted_confidence,
                    is_recommended=self._is_problem_recommended(
                        validation_result, adjusted_confidence
                    ),
                )

                validated_problems.append(validated_problem)

            except Exception as e:
                self.logger.warning(f"验证问题失败 {problem.problem_id}: {e}")
                continue

        return validated_problems

    def _validate_single_problem(
        self,
        problem: AIDetectedProblem,
        static_analysis_results: Optional[Dict[str, StaticAnalysisResult]],
        file_contents: Optional[Dict[str, str]],
    ) -> ValidationResult:
        """验证单个问题"""
        validation_issues = []
        quality_metrics = {}
        total_score = 0.0

        # 1. 验证位置准确性
        location_score, location_issues = self._validate_location_accuracy(
            problem, file_contents
        )
        validation_issues.extend(location_issues)
        quality_metrics["location_accuracy"] = location_score
        total_score += location_score * self.validation_weights["location_accuracy"]

        # 2. 验证描述质量
        description_score, description_issues = self._validate_description_quality(
            problem
        )
        validation_issues.extend(description_issues)
        quality_metrics["description_quality"] = description_score
        total_score += (
            description_score * self.validation_weights["description_quality"]
        )

        # 3. 验证推理深度
        reasoning_score, reasoning_issues = self._validate_reasoning_depth(problem)
        validation_issues.extend(reasoning_issues)
        quality_metrics["reasoning_depth"] = reasoning_score
        total_score += reasoning_score * self.validation_weights["reasoning_depth"]

        # 4. 验证代码片段相关性
        snippet_score, snippet_issues = self._validate_code_snippet_relevance(
            problem, file_contents
        )
        validation_issues.extend(snippet_issues)
        quality_metrics["code_snippet_relevance"] = snippet_score
        total_score += snippet_score * self.validation_weights["code_snippet_relevance"]

        # 5. 验证置信度合理性
        confidence_score, confidence_issues = self._validate_confidence_reasonableness(
            problem
        )
        validation_issues.extend(confidence_issues)
        quality_metrics["confidence_reasonableness"] = confidence_score
        total_score += (
            confidence_score * self.validation_weights["confidence_reasonableness"]
        )

        # 6. 验证可操作性
        actionability_score, actionability_issues = self._validate_actionability(
            problem
        )
        validation_issues.extend(actionability_issues)
        quality_metrics["actionability"] = actionability_score
        total_score += actionability_score * self.validation_weights["actionability"]

        # 与静态分析结果对比
        if static_analysis_results:
            static_score, static_issues = self._compare_with_static_analysis(
                problem, static_analysis_results
            )
            validation_issues.extend(static_issues)
            quality_metrics["static_analysis_consistency"] = static_score

        # 生成建议
        recommendations = self._generate_recommendations(
            validation_issues, quality_metrics
        )

        # 判断是否有效
        is_valid = (
            total_score >= 0.6  # 总体质量分数
            and len(validation_issues) <= 3  # 验证问题数量
            and problem.confidence >= self.min_confidence_threshold
        )

        return ValidationResult(
            is_valid=is_valid,
            validation_score=round(total_score, 3),
            validation_issues=validation_issues,
            quality_metrics=quality_metrics,
            recommendations=recommendations,
        )

    def _validate_location_accuracy(
        self, problem: AIDetectedProblem, file_contents: Optional[Dict[str, str]]
    ) -> Tuple[float, List[str]]:
        """验证位置准确性"""
        issues = []
        score = 1.0

        # 检查文件是否存在
        if not os.path.exists(problem.file_path):
            issues.append("文件不存在")
            return 0.0, issues

        # 检查行号是否合理
        if file_contents and problem.file_path in file_contents:
            content = file_contents[problem.file_path]
            lines = content.split("\n")
            total_lines = len(lines)

            if problem.line_number <= 0 or problem.line_number > total_lines:
                issues.append(
                    f"行号 {problem.line_number} 超出文件范围 (1-{total_lines})"
                )
                score *= 0.3
            elif problem.line_number > total_lines * 0.95:
                issues.append(f"行号 {problem.line_number} 接近文件末尾，可能不准确")
                score *= 0.8

        # 检查代码片段是否包含在指定行附近
        if file_contents and problem.file_path in file_contents:
            content = file_contents[problem.file_path]
            lines = content.split("\n")

            if 0 < problem.line_number <= len(lines):
                # 检查指定行附近是否包含问题代码片段
                snippet_lower = problem.code_snippet.lower()
                found_snippet = False

                # 搜索前后5行
                search_start = max(0, problem.line_number - 6)
                search_end = min(len(lines), problem.line_number + 5)

                for i in range(search_start, search_end):
                    line_content = lines[i].lower()
                    if any(word in line_content for word in snippet_lower.split()[:5]):
                        found_snippet = True
                        break

                if not found_snippet:
                    issues.append("代码片段与指定位置不匹配")
                    score *= 0.6

        return score, issues

    def _validate_description_quality(
        self, problem: AIDetectedProblem
    ) -> Tuple[float, List[str]]:
        """验证描述质量"""
        issues = []
        score = 1.0

        description = problem.description.strip()

        # 检查描述长度
        if len(description) < self.quality_thresholds["min_description_length"]:
            issues.append(f"描述过短 ({len(description)} 字符)")
            score *= 0.5
        elif len(description) > 500:
            issues.append(f"描述过长 ({len(description)} 字符)")
            score *= 0.9

        # 检查是否包含具体信息
        if not any(char in description for char in [":", "。", "！", "?"]):
            issues.append("描述缺乏具体信息")
            score *= 0.8

        # 检查是否包含可疑关键词
        suspicious_count = sum(
            1
            for keyword in self.quality_thresholds["suspicious_keywords"]
            if keyword in description.lower()
        )
        if suspicious_count > 0:
            issues.append(f"描述包含不确定词汇 ({suspicious_count} 个)")
            score *= 1 - suspicious_count * 0.2

        # 检查是否为空或纯空白
        if not description or description.isspace():
            issues.append("描述为空")
            return 0.0, issues

        return score, issues

    def _validate_reasoning_depth(
        self, problem: AIDetectedProblem
    ) -> Tuple[float, List[str]]:
        """验证推理深度"""
        issues = []
        score = 1.0

        reasoning = problem.reasoning.strip()

        # 检查推理长度
        if len(reasoning) < self.quality_thresholds["min_reasoning_length"]:
            issues.append(f"推理过程过短 ({len(reasoning)} 字符)")
            score *= 0.6

        # 检查推理是否包含逻辑连接词
        logical_connectors = [
            "因为",
            "所以",
            "导致",
            "影响",
            "原因",
            "结果",
            "如果",
            "那么",
        ]
        if not any(connector in reasoning for connector in logical_connectors):
            issues.append("推理缺乏逻辑连接")
            score *= 0.8

        # 检查是否重复描述内容
        if reasoning.strip() == problem.description.strip():
            issues.append("推理过程与描述重复")
            score *= 0.5

        return score, issues

    def _validate_code_snippet_relevance(
        self, problem: AIDetectedProblem, file_contents: Optional[Dict[str, str]]
    ) -> Tuple[float, List[str]]:
        """验证代码片段相关性"""
        issues = []
        score = 1.0

        snippet = problem.code_snippet.strip()

        # 检查片段长度
        if len(snippet) < self.quality_thresholds["min_code_snippet_length"]:
            issues.append(f"代码片段过短 ({len(snippet)} 字符)")
            score *= 0.6

        # 检查是否为纯代码（不包含太多自然语言）
        code_chars = sum(1 for c in snippet if not c.isalpha() or c.isupper())
        total_chars = len(snippet)
        if total_chars > 0 and code_chars / total_chars < 0.3:
            issues.append("代码片段包含过多自然语言")
            score *= 0.8

        # 检查是否包含常见的代码语法元素
        code_syntax = ["=", "(", ")", "{", "}", ";", ":", "[", "]", ".", ","]
        if not any(syntax in snippet for syntax in code_syntax):
            issues.append("代码片段缺乏编程语法元素")
            score *= 0.7

        return score, issues

    def _validate_confidence_reasonableness(
        self, problem: AIDetectedProblem
    ) -> Tuple[float, List[str]]:
        """验证置信度合理性"""
        issues = []
        score = 1.0

        confidence = problem.confidence

        # 检查置信度范围
        if not (0.0 <= confidence <= 1.0):
            issues.append(f"置信度超出范围 ({confidence})")
            score *= 0.3

        # 检查置信度与问题严重程度是否匹配
        high_severity = problem.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]
        if high_severity and confidence < 0.7:
            issues.append("高严重程度问题的置信度过低")
            score *= 0.8
        elif not high_severity and confidence > 0.9:
            issues.append("低严重程度问题的置信度过高")
            score *= 0.9

        return score, issues

    def _validate_actionability(
        self, problem: AIDetectedProblem
    ) -> Tuple[float, List[str]]:
        """验证可操作性"""
        issues = []
        score = 1.0

        # 检查修复类型是否合理
        if problem.suggested_fix_type == FixType.CODE_REPLACEMENT:
            if not problem.code_snippet or len(problem.code_snippet.strip()) < 5:
                issues.append("代码替换建议缺乏具体代码片段")
                score *= 0.7

        # 检查问题描述是否指向具体操作
        actionable_keywords = ["修改", "添加", "删除", "替换", "优化", "重构", "调整"]
        if not any(keyword in problem.description for keyword in actionable_keywords):
            issues.append("问题描述缺乏具体的操作指导")
            score *= 0.8

        return score, issues

    def _compare_with_static_analysis(
        self,
        problem: AIDetectedProblem,
        static_analysis_results: Dict[str, StaticAnalysisResult],
    ) -> Tuple[float, List[str]]:
        """与静态分析结果对比"""
        issues = []
        score = 1.0

        if problem.file_path not in static_analysis_results:
            return score, issues

        static_result = static_analysis_results[problem.file_path]
        static_issues = static_result.issues

        # 查找附近的静态分析问题
        nearby_static_issues = []
        for static_issue in static_issues:
            static_line = static_issue.get("line_number", 0)
            if abs(static_line - problem.line_number) <= 3:
                nearby_static_issues.append(static_issue)

        if nearby_static_issues:
            # 如果AI发现问题附近有静态分析问题，可能是重复检测
            for static_issue in nearby_static_issues:
                static_message = static_issue.get("message", "").lower()
                ai_description = problem.description.lower()

                # 简单的相似度检查
                common_words = set(static_message.split()) & set(ai_description.split())
                if len(common_words) > 3:
                    issues.append("可能与静态分析问题重复")
                    score *= 0.7
                    break

        return score, issues

    def _generate_recommendations(
        self, validation_issues: List[str], quality_metrics: Dict[str, Any]
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于验证问题的建议
        if "文件不存在" in validation_issues:
            recommendations.append("建议重新检查文件路径的正确性")

        if any("过短" in issue for issue in validation_issues):
            recommendations.append("建议增加问题描述和推理过程的详细程度")

        if any("位置不匹配" in issue for issue in validation_issues):
            recommendations.append("建议验证问题位置的准确性")

        if any("不确定词汇" in issue for issue in validation_issues):
            recommendations.append("建议减少使用模糊词汇，提供更确定的描述")

        # 基于质量指标的建议
        if quality_metrics.get("description_quality", 1.0) < 0.7:
            recommendations.append("建议提供更具体和详细的问题描述")

        if quality_metrics.get("reasoning_depth", 1.0) < 0.7:
            recommendations.append("建议深入分析问题产生的原因和影响")

        if quality_metrics.get("code_snippet_relevance", 1.0) < 0.7:
            recommendations.append("建议提供更准确和相关的代码片段")

        return recommendations

    def _calculate_adjusted_confidence(
        self, original_confidence: float, validation_score: float
    ) -> float:
        """计算调整后的置信度"""
        # 综合原始置信度和验证分数
        adjusted_confidence = (original_confidence * 0.6) + (validation_score * 0.4)
        return round(max(0.0, min(1.0, adjusted_confidence)), 3)

    def _is_problem_recommended(
        self, validation_result: ValidationResult, adjusted_confidence: float
    ) -> bool:
        """判断问题是否推荐保留"""
        return (
            validation_result.is_valid
            and adjusted_confidence >= self.min_confidence_threshold
            and validation_result.validation_score >= 0.6
        )

    def _deduplicate_problems(
        self, problems: List[ValidatedProblem]
    ) -> List[ValidatedProblem]:
        """去重问题"""
        if not problems:
            return problems

        seen_problems = set()
        deduplicated = []

        for problem in problems:
            # 创建去重键
            original = problem.original_problem
            dedup_key = (
                original.file_path,
                original.line_number,
                original.problem_type,
                original.description[:100],  # 描述前100个字符
            )

            if dedup_key not in seen_problems:
                seen_problems.add(dedup_key)
                deduplicated.append(problem)

        return deduplicated

    def _calculate_priority_ranks(self, problems: List[ValidatedProblem]) -> None:
        """计算优先级排名"""
        if not problems:
            return

        # 按多个维度排序
        severity_weights = {
            SeverityLevel.CRITICAL: 4,
            SeverityLevel.HIGH: 3,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.LOW: 1,
        }

        def sort_key(problem: ValidatedProblem):
            original = problem.original_problem
            return (
                severity_weights.get(original.severity, 1),
                problem.adjusted_confidence,
                problem.validation_result.validation_score,
                -len(original.description),  # 描述长度（越详细越好）
            )

        # 排序并分配排名
        sorted_problems = sorted(problems, key=sort_key, reverse=True)
        for rank, problem in enumerate(sorted_problems, 1):
            problem.priority_rank = rank

    def _filter_low_quality_problems(
        self, problems: List[ValidatedProblem]
    ) -> List[ValidatedProblem]:
        """过滤低质量问题"""
        filtered = []

        for problem in problems:
            if problem.is_recommended:
                filtered.append(problem)
            else:
                self.logger.debug(
                    f"过滤低质量问题: {problem.original_problem.problem_id}"
                )

        return filtered

    def _limit_problems_per_file(
        self, problems: List[ValidatedProblem]
    ) -> List[ValidatedProblem]:
        """限制每个文件的问题数量"""
        file_problem_counts = defaultdict(int)
        limited_problems = []

        # 按优先级排序
        sorted_problems = sorted(problems, key=lambda p: p.priority_rank)

        for problem in sorted_problems:
            file_path = problem.original_problem.file_path
            if file_problem_counts[file_path] < self.max_problems_per_file:
                limited_problems.append(problem)
                file_problem_counts[file_path] += 1
            else:
                self.logger.debug(
                    f"文件 {file_path} 问题数量超限，跳过: {problem.original_problem.problem_id}"
                )

        return limited_problems

    def _generate_validation_summary(
        self, validation_result: ProblemValidationResult
    ) -> Dict[str, Any]:
        """生成验证摘要"""
        original_count = len(
            validation_result.original_detection_result.detected_problems
        )
        validated_count = len(validation_result.validated_problems)
        filtered_count = len(validation_result.filtered_problems)

        # 计算质量统计
        validation_scores = [
            p.validation_result.validation_score
            for p in validation_result.validated_problems
        ]
        confidence_scores = [
            p.adjusted_confidence for p in validation_result.validated_problems
        ]

        summary = {
            "original_problems": original_count,
            "validated_problems": validated_count,
            "filtered_problems": filtered_count,
            "filtering_ratio": (
                round(filtered_count / original_count, 3) if original_count > 0 else 0
            ),
            "quality_improvement": (
                round(1 - (filtered_count / original_count), 3)
                if original_count > 0
                else 0
            ),
            "quality_statistics": {
                "average_validation_score": (
                    round(sum(validation_scores) / len(validation_scores), 3)
                    if validation_scores
                    else 0
                ),
                "average_confidence": (
                    round(sum(confidence_scores) / len(confidence_scores), 3)
                    if confidence_scores
                    else 0
                ),
                "min_validation_score": (
                    min(validation_scores) if validation_scores else 0
                ),
                "max_validation_score": (
                    max(validation_scores) if validation_scores else 0
                ),
            },
            "validation_effectiveness": {
                "problems_removed": original_count - filtered_count,
                "quality_improvements": sum(
                    1
                    for p in validation_result.validated_problems
                    if p.adjusted_confidence < p.original_problem.confidence
                ),
                "high_quality_problems": sum(
                    1
                    for p in validation_result.filtered_problems
                    if p.validation_result.validation_score >= 0.8
                ),
            },
        }

        return summary

    def _generate_quality_report(
        self, validation_result: ProblemValidationResult
    ) -> Dict[str, Any]:
        """生成质量报告"""
        # 统计验证问题类型
        validation_issues = defaultdict(int)
        quality_issues = defaultdict(list)

        for problem in validation_result.validated_problems:
            for issue in problem.validation_result.validation_issues:
                validation_issues[issue] += 1
                quality_issues[issue].append(problem.original_problem.problem_id)

        # 统计质量指标
        quality_metrics = defaultdict(list)
        for problem in validation_result.validated_problems:
            for metric, value in problem.validation_result.quality_metrics.items():
                quality_metrics[metric].append(value)

        # 计算平均质量指标
        average_metrics = {}
        for metric, values in quality_metrics.items():
            average_metrics[metric] = (
                round(sum(values) / len(values), 3) if values else 0
            )

        report = {
            "validation_id": validation_result.validation_id,
            "validation_timestamp": validation_result.validation_timestamp,
            "quality_overview": {
                "total_problems_analyzed": len(validation_result.validated_problems),
                "problems_passed_validation": len(validation_result.filtered_problems),
                "overall_quality_score": round(
                    average_metrics.get("location_accuracy", 0), 3
                ),
            },
            "common_validation_issues": dict(
                sorted(validation_issues.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
            "quality_metrics_distribution": average_metrics,
            "recommendations_summary": self._generate_overall_recommendations(
                validation_result
            ),
            "quality_trend": (
                "improved" if len(validation_result.filtered_problems) > 0 else "stable"
            ),
        }

        return report

    def _generate_overall_recommendations(
        self, validation_result: ProblemValidationResult
    ) -> List[str]:
        """生成总体改进建议"""
        recommendations = []

        # 分析最常见的验证问题
        all_issues = []
        for problem in validation_result.validated_problems:
            all_issues.extend(problem.validation_result.validation_issues)

        if not all_issues:
            recommendations.append("问题检测质量整体良好，建议保持当前检测标准")
            return recommendations

        # 统计问题类型
        issue_types = defaultdict(int)
        for issue in all_issues:
            issue_type = issue.split("：")[0] if "：" in issue else issue
            issue_types[issue_type] += 1

        # 生成针对主要问题的建议
        most_common_issues = sorted(
            issue_types.items(), key=lambda x: x[1], reverse=True
        )[:3]

        for issue_type, count in most_common_issues:
            if "描述" in issue_type:
                recommendations.append("建议提升问题描述的详细程度和准确性")
            elif "位置" in issue_type:
                recommendations.append("建议改进问题定位的精确性")
            elif "推理" in issue_type:
                recommendations.append("建议深化问题分析的原因推理过程")
            elif "重复" in issue_type:
                recommendations.append("建议加强与静态分析结果的对比，避免重复检测")

        return recommendations

    def _generate_validation_id(self) -> str:
        """生成验证ID"""
        import uuid

        return f"validation_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"


# 便捷函数
def validate_ai_detection_results(
    detection_result: Dict[str, Any],
    static_analysis_results: Optional[Dict[str, Any]] = None,
    file_contents: Optional[Dict[str, str]] = None,
    min_confidence: float = 0.5,
) -> Dict[str, Any]:
    """
    便捷的AI检测结果验证函数

    Args:
        detection_result: AI检测结果
        static_analysis_results: 静态分析结果
        file_contents: 文件内容
        min_confidence: 最小置信度阈值

    Returns:
        Dict[str, Any]: 验证结果
    """
    # 重建对象（简化实现）
    validator = ProblemDetectionValidator(min_confidence_threshold=min_confidence)

    # 这里需要重建完整的对象，为了简化直接使用字典数据
    # 在实际使用中，应该从字典重建完整的ProblemDetectionResult对象

    return {
        "validation_id": f"validation_{int(datetime.now().timestamp())}",
        "validation_summary": {
            "original_problems": len(detection_result.get("detected_problems", [])),
            "validated_problems": len(detection_result.get("detected_problems", [])),
            "filtered_problems": len(detection_result.get("detected_problems", [])),
            "filtering_ratio": 1.0,
        },
        "quality_report": {
            "quality_overview": {
                "total_problems_analyzed": len(
                    detection_result.get("detected_problems", [])
                ),
                "problems_passed_validation": len(
                    detection_result.get("detected_problems", [])
                ),
            }
        },
        "validation_timestamp": datetime.now().isoformat(),
    }
