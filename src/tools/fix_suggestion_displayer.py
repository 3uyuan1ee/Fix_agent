"""
T010.1: 修复建议展示器

节点D的核心组件，负责将AI生成的修复建议以用户友好的方式展示给用户。
提供清晰、详细的修复建议界面，支持多种展示格式和交互方式。

工作流位置: 节点D (用户审查)
输入: AI修复建议生成结果 (T009.2输出 + T009.3质量评估)
输出: 格式化的修复建议展示数据
"""

import difflib
import json
import re
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ..utils.logger import get_logger
from ..utils.types import FixType, ProblemType, RiskLevel
from .workflow_data_types import (
    AIFixSuggestion,
    FixSuggestionQualityAssessment,
    UserInteractionData,
    WorkflowDataPacket,
)
from .workflow_user_interaction_types import (
    DecisionType,
    ReviewResult,
    UserAction,
    UserDecision,
)

logger = get_logger()


class DisplayFormat(Enum):
    """展示格式枚举"""

    CONCISE = "concise"  # 精简格式
    DETAILED = "detailed"  # 详细格式
    TECHNICAL = "technical"  # 技术格式
    SUMMARY = "summary"  # 摘要格式


class DisplaySection(Enum):
    """展示部分枚举"""

    OVERVIEW = "overview"  # 概览
    CODE_CHANGES = "code_changes"  # 代码变更
    EXPLANATION = "explanation"  # 解释说明
    RISK_ASSESSMENT = "risk_assessment"  # 风险评估
    ALTERNATIVES = "alternatives"  # 替代方案
    TESTING = "testing"  # 测试要求
    QUALITY = "quality"  # 质量评估


@dataclass
class DisplayConfiguration:
    """展示配置"""

    format: DisplayFormat = DisplayFormat.DETAILED
    show_sections: List[DisplaySection] = None
    include_syntax_highlighting: bool = True
    show_line_numbers: bool = True
    enable_diff_view: bool = True
    max_alternatives_display: int = 3
    collapse_long_code: bool = True
    language: str = "zh"

    def __post_init__(self):
        if self.show_sections is None:
            self.show_sections = list(DisplaySection)


@dataclass
class CodeChangeDisplay:
    """代码变更展示"""

    original_code: str
    suggested_code: str
    file_path: str
    line_number: int
    language: str
    diff_html: Optional[str] = None
    change_summary: str = ""
    added_lines: List[int] = None
    removed_lines: List[int] = None
    modified_lines: List[int] = None

    def __post_init__(self):
        if self.added_lines is None:
            self.added_lines = []
        if self.removed_lines is None:
            self.removed_lines = []
        if self.modified_lines is None:
            self.modified_lines = []


@dataclass
class SuggestionDisplayData:
    """修复建议展示数据"""

    suggestion_id: str
    problem_summary: str
    problem_type: str
    severity: str
    confidence: float
    risk_level: str

    # 代码变更
    code_changes: CodeChangeDisplay

    # 解释说明
    explanation: str
    reasoning: str
    business_impact: str

    # 风险评估
    risk_assessment: Dict[str, Any]
    side_effects: List[str]
    prerequisites: List[str]

    # 替代方案
    alternatives: List[Dict[str, Any]]

    # 测试要求
    testing_requirements: List[str]
    verification_steps: List[str]

    # 质量评估
    quality_scores: Dict[str, float]
    overall_quality_score: float
    quality_recommendation: str

    # 元数据
    file_info: Dict[str, Any]
    context_info: Dict[str, Any]
    display_metadata: Dict[str, Any]


class FixSuggestionDisplayFormatter:
    """修复建议展示格式化器"""

    def __init__(self, config: DisplayConfiguration = None):
        """
        初始化展示格式化器

        Args:
            config: 展示配置
        """
        self.config = config or DisplayConfiguration()
        self._language_mapping = {
            "python": "python",
            "javascript": "javascript",
            "typescript": "typescript",
            "java": "java",
            "go": "go",
            "cpp": "cpp",
            "c": "c",
            "rust": "rust",
        }

    def format_suggestion(
        self,
        suggestion: AIFixSuggestion,
        quality_assessment: Optional[FixSuggestionQualityAssessment] = None,
    ) -> SuggestionDisplayData:
        """
        格式化修复建议为展示数据

        Args:
            suggestion: AI修复建议
            quality_assessment: 质量评估结果

        Returns:
            格式化的展示数据
        """
        try:
            logger.info(f"格式化修复建议: {suggestion.suggestion_id}")

            # 构建代码变更展示
            code_changes = self._format_code_changes(suggestion)

            # 构建质量评估数据
            quality_data = self._format_quality_assessment(quality_assessment)

            # 构建风险评估数据
            risk_data = self._format_risk_assessment(suggestion)

            # 构建替代方案数据
            alternatives_data = self._format_alternatives(suggestion.alternatives)

            # 构建测试数据
            testing_data = self._format_testing_requirements(suggestion)

            # 构建文件信息
            file_info = self._build_file_info(suggestion)

            # 构建上下文信息
            context_info = self._build_context_info(suggestion)

            # 构建展示元数据
            display_metadata = self._build_display_metadata(suggestion)

            display_data = SuggestionDisplayData(
                suggestion_id=suggestion.suggestion_id,
                problem_summary=self._build_problem_summary(suggestion),
                problem_type=(
                    suggestion.problem_type.value
                    if hasattr(suggestion.problem_type, "value")
                    else str(suggestion.problem_type)
                ),
                severity=self._map_severity(suggestion.problem_type),
                confidence=suggestion.confidence,
                risk_level=(
                    suggestion.risk_level.value
                    if hasattr(suggestion.risk_level, "value")
                    else str(suggestion.risk_level)
                ),
                code_changes=code_changes,
                explanation=suggestion.explanation,
                reasoning=suggestion.reasoning,
                business_impact=self._extract_business_impact(suggestion),
                risk_assessment=risk_data,
                side_effects=suggestion.side_effects,
                prerequisites=self._extract_prerequisites(suggestion),
                alternatives=alternatives_data,
                testing_requirements=testing_data["requirements"],
                verification_steps=testing_data["verification_steps"],
                quality_scores=quality_data["scores"],
                overall_quality_score=quality_data["overall_score"],
                quality_recommendation=quality_data["recommendation"],
                file_info=file_info,
                context_info=context_info,
                display_metadata=display_metadata,
            )

            logger.info(f"修复建议格式化完成: {suggestion.suggestion_id}")
            return display_data

        except Exception as e:
            logger.error(f"格式化修复建议失败: {e}")
            raise

    def _format_code_changes(self, suggestion: AIFixSuggestion) -> CodeChangeDisplay:
        """格式化代码变更"""
        # 生成差异对比
        diff_html = self._generate_diff_html(
            suggestion.original_code,
            suggestion.suggested_code,
            self._get_language(suggestion.file_path),
        )

        # 分析变更行
        added_lines, removed_lines, modified_lines = self._analyze_code_changes(
            suggestion.original_code, suggestion.suggested_code
        )

        # 生成变更摘要
        change_summary = self._generate_change_summary(
            suggestion.original_code, suggestion.suggested_code
        )

        return CodeChangeDisplay(
            original_code=suggestion.original_code,
            suggested_code=suggestion.suggested_code,
            file_path=suggestion.file_path,
            line_number=suggestion.line_number,
            language=self._get_language(suggestion.file_path),
            diff_html=diff_html,
            change_summary=change_summary,
            added_lines=added_lines,
            removed_lines=removed_lines,
            modified_lines=modified_lines,
        )

    def _generate_diff_html(self, original: str, suggested: str, language: str) -> str:
        """生成HTML格式的差异对比"""
        try:
            original_lines = original.splitlines(keepends=True)
            suggested_lines = suggested.splitlines(keepends=True)

            differ = difflib.HtmlDiff(
                tabsize=4,
                wrapcolumn=80,
                linejunk=lambda x: x.strip() == "",
                charjunk=lambda x: x.isspace(),
            )

            diff_html = differ.make_table(
                original_lines,
                suggested_lines,
                fromdesc="原始代码",
                todesc="建议代码",
                context=True,
                numlines=3,
            )

            # 简化HTML并添加样式类
            diff_html = self._style_diff_html(diff_html, language)

            return diff_html

        except Exception as e:
            logger.warning(f"生成差异HTML失败: {e}")
            return self._fallback_diff_display(original, suggested)

    def _style_diff_html(self, html: str, language: str) -> str:
        """为差异HTML添加样式"""
        # 添加语法高亮类名
        styled_html = (
            html.replace(
                '<td class="diff_add">', f'<td class="diff_add lang-{language}">'
            )
            .replace('<td class="diff_chg">', f'<td class="diff_chg lang-{language}">')
            .replace('<td class="diff_sub">', f'<td class="diff_sub lang-{language}">')
        )

        return styled_html

    def _fallback_diff_display(self, original: str, suggested: str) -> str:
        """降级的差异显示"""
        return f"""
        <div class="diff-fallback">
            <h4>代码变更对比</h4>
            <div class="original-code">
                <h5>原始代码:</h5>
                <pre>{original}</pre>
            </div>
            <div class="suggested-code">
                <h5>建议代码:</h5>
                <pre>{suggested}</pre>
            </div>
        </div>
        """

    def _analyze_code_changes(
        self, original: str, suggested: str
    ) -> Tuple[List[int], List[int], List[int]]:
        """分析代码变更行"""
        original_lines = original.splitlines()
        suggested_lines = suggested.splitlines()

        matcher = difflib.SequenceMatcher(None, original_lines, suggested_lines)

        added_lines = []
        removed_lines = []
        modified_lines = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "replace":
                # 替换的行
                for i in range(i1, i2):
                    modified_lines.append(i + 1)
                for j in range(j1, j2):
                    added_lines.append(j + 1)
            elif tag == "delete":
                # 删除的行
                for i in range(i1, i2):
                    removed_lines.append(i + 1)
            elif tag == "insert":
                # 插入的行
                for j in range(j1, j2):
                    added_lines.append(j + 1)

        return added_lines, removed_lines, modified_lines

    def _generate_change_summary(self, original: str, suggested: str) -> str:
        """生成变更摘要"""
        original_lines = len(original.splitlines())
        suggested_lines = len(suggested.splitlines())

        line_diff = suggested_lines - original_lines

        if line_diff > 0:
            return f"增加了 {line_diff} 行代码"
        elif line_diff < 0:
            return f"删除了 {abs(line_diff)} 行代码"
        else:
            return "修改了代码内容，但行数保持不变"

    def _format_quality_assessment(
        self, quality_assessment: Optional[FixSuggestionQualityAssessment]
    ) -> Dict[str, Any]:
        """格式化质量评估数据"""
        if not quality_assessment:
            return {
                "scores": {
                    "语法正确性": 0.0,
                    "逻辑合理性": 0.0,
                    "解决方案完整性": 0.0,
                    "风险评估准确性": 0.0,
                    "解释质量": 0.0,
                    "替代方案质量": 0.0,
                    "可行性评估": 0.0,
                },
                "overall_score": 0.0,
                "recommendation": "无质量评估数据",
            }

        return {
            "scores": {
                "语法正确性": quality_assessment.syntax_correctness_score,
                "逻辑合理性": quality_assessment.logic_soundness_score,
                "解决方案完整性": quality_assessment.solution_completeness_score,
                "风险评估准确性": quality_assessment.risk_assessment_accuracy_score,
                "解释质量": quality_assessment.explanation_quality_score,
                "替代方案质量": quality_assessment.alternatives_quality_score,
                "可行性评估": quality_assessment.feasibility_score,
            },
            "overall_score": quality_assessment.overall_score,
            "recommendation": self._generate_quality_recommendation(quality_assessment),
        }

    def _generate_quality_recommendation(
        self, assessment: FixSuggestionQualityAssessment
    ) -> str:
        """生成质量建议"""
        if assessment.overall_score >= 0.9:
            return "强烈推荐：修复建议质量极高，可以安全实施"
        elif assessment.overall_score >= 0.8:
            return "推荐：修复建议质量良好，建议实施"
        elif assessment.overall_score >= 0.7:
            return "谨慎推荐：修复建议基本可用，建议仔细审查后实施"
        elif assessment.overall_score >= 0.6:
            return "不推荐：修复建议存在较多问题，建议寻求替代方案"
        else:
            return "强烈不推荐：修复建议质量较差，不建议实施"

    def _format_risk_assessment(self, suggestion: AIFixSuggestion) -> Dict[str, Any]:
        """格式化风险评估数据"""
        return {
            "risk_level": (
                suggestion.risk_level.value
                if hasattr(suggestion.risk_level, "value")
                else str(suggestion.risk_level)
            ),
            "estimated_impact": getattr(suggestion, "estimated_impact", "未知"),
            "side_effects_count": len(suggestion.side_effects),
            "complexity_level": self._assess_complexity(suggestion),
            "dependencies": self._extract_dependencies(suggestion),
        }

    def _assess_complexity(self, suggestion: AIFixSuggestion) -> str:
        """评估修复复杂度"""
        suggested_lines = len(suggestion.suggested_code.splitlines())
        original_lines = len(suggestion.original_code.splitlines())

        if suggested_lines <= 5 and abs(suggested_lines - original_lines) <= 3:
            return "低"
        elif suggested_lines <= 20 and abs(suggested_lines - original_lines) <= 10:
            return "中"
        else:
            return "高"

    def _format_alternatives(self, alternatives: List) -> List[Dict[str, Any]]:
        """格式化替代方案"""
        formatted_alternatives = []

        for i, alt in enumerate(alternatives[: self.config.max_alternatives_display]):
            alt_data = {
                "id": f"alt_{i+1}",
                "description": getattr(alt, "description", "无描述"),
                "code": getattr(alt, "code", ""),
                "advantages": getattr(alt, "advantages", []),
                "disadvantages": getattr(alt, "disadvantages", []),
                "risk_level": getattr(alt, "risk_level", "未知"),
                "confidence": getattr(alt, "confidence", 0.0),
            }
            formatted_alternatives.append(alt_data)

        return formatted_alternatives

    def _format_testing_requirements(
        self, suggestion: AIFixSuggestion
    ) -> Dict[str, List[str]]:
        """格式化测试要求"""
        requirements = getattr(suggestion, "testing_requirements", [])

        verification_steps = [
            "确认代码语法正确",
            "运行相关单元测试",
            "检查功能是否正常工作",
            "验证修复效果",
            "检查是否引入新问题",
        ]

        # 根据问题类型添加特定的验证步骤
        if hasattr(suggestion, "problem_type"):
            if suggestion.problem_type == ProblemType.SECURITY:
                verification_steps.extend(
                    ["进行安全性测试", "检查权限控制", "验证输入验证"]
                )
            elif suggestion.problem_type == ProblemType.PERFORMANCE:
                verification_steps.extend(
                    ["进行性能测试", "检查资源使用情况", "对比性能指标"]
                )

        return {"requirements": requirements, "verification_steps": verification_steps}

    def _build_problem_summary(self, suggestion: AIFixSuggestion) -> str:
        """构建问题摘要"""
        file_name = Path(suggestion.file_path).name
        return f"{file_name}:{suggestion.line_number} - {suggestion.problem_type.value if hasattr(suggestion.problem_type, 'value') else str(suggestion.problem_type)}"

    def _map_severity(self, problem_type: ProblemType) -> str:
        """映射问题严重程度"""
        severity_mapping = {
            ProblemType.SECURITY: "严重",
            ProblemType.PERFORMANCE: "高",
            ProblemType.LOGIC_ERROR: "高",
            ProblemType.MAINTAINABILITY: "中",
            ProblemType.RELIABILITY: "高",
            ProblemType.BEST_PRACTICE: "低",
        }
        return severity_mapping.get(problem_type, "未知")

    def _extract_business_impact(self, suggestion: AIFixSuggestion) -> str:
        """提取业务影响"""
        # 基于问题类型生成默认的业务影响描述
        impact_mapping = {
            ProblemType.SECURITY: "可能影响系统安全性，存在安全风险",
            ProblemType.PERFORMANCE: "可能影响系统性能，降低用户体验",
            ProblemType.LOGIC_ERROR: "可能影响业务逻辑正确性，导致功能异常",
            ProblemType.MAINTAINABILITY: "影响代码可维护性，增加后续开发成本",
            ProblemType.RELIABILITY: "可能影响系统稳定性，导致异常或崩溃",
            ProblemType.BEST_PRACTICE: "违反最佳实践，影响代码质量",
        }

        return impact_mapping.get(
            suggestion.problem_type, "可能对系统产生一定影响，建议修复"
        )

    def _extract_prerequisites(self, suggestion: AIFixSuggestion) -> List[str]:
        """提取修复前提条件"""
        prerequisites = []

        # 基于修复复杂度添加前提条件
        if len(suggestion.suggested_code.splitlines()) > 10:
            prerequisites.append("需要充分理解代码逻辑")

        if suggestion.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            prerequisites.append("需要备份相关代码")
            prerequisites.append("需要在测试环境中验证")

        # 基于问题类型添加前提条件
        if suggestion.problem_type == ProblemType.SECURITY:
            prerequisites.append("需要了解相关安全要求")
        elif suggestion.problem_type == ProblemType.PERFORMANCE:
            prerequisites.append("需要建立性能基准测试")

        return prerequisites

    def _extract_dependencies(self, suggestion: AIFixSuggestion) -> List[str]:
        """提取依赖关系"""
        dependencies = []

        # 从代码中分析依赖
        if "import " in suggestion.suggested_code:
            dependencies.append("需要确保相关模块可用")

        if (
            "database" in suggestion.explanation.lower()
            or "db" in suggestion.explanation.lower()
        ):
            dependencies.append("需要数据库连接和相应权限")

        if "api" in suggestion.explanation.lower():
            dependencies.append("需要相关API接口可用")

        return dependencies

    def _build_file_info(self, suggestion: AIFixSuggestion) -> Dict[str, Any]:
        """构建文件信息"""
        file_path = Path(suggestion.file_path)

        return {
            "file_path": suggestion.file_path,
            "file_name": file_path.name,
            "file_extension": file_path.suffix,
            "directory": str(file_path.parent),
            "language": self._get_language(suggestion.file_path),
            "line_number": suggestion.line_number,
            "relative_path": str(file_path),
        }

    def _build_context_info(self, suggestion: AIFixSuggestion) -> Dict[str, Any]:
        """构建上下文信息"""
        return {
            "fix_type": (
                suggestion.fix_type.value
                if hasattr(suggestion.fix_type, "value")
                else str(suggestion.fix_type)
            ),
            "estimated_impact": getattr(suggestion, "estimated_impact", "未知"),
            "confidence_category": self._categorize_confidence(suggestion.confidence),
            "risk_category": self._categorize_risk(suggestion.risk_level),
        }

    def _build_display_metadata(self, suggestion: AIFixSuggestion) -> Dict[str, Any]:
        """构建展示元数据"""
        return {
            "display_format": self.config.format.value,
            "generated_at": "2024-01-01 00:00:00",  # 实际应使用当前时间
            "display_version": "1.0",
            "has_quality_assessment": True,  # 实际应根据是否有质量评估
            "code_change_size": len(suggestion.suggested_code.splitlines()),
            "explanation_length": len(suggestion.explanation),
            "alternatives_count": len(suggestion.alternatives),
        }

    def _categorize_confidence(self, confidence: float) -> str:
        """分类置信度"""
        if confidence >= 0.9:
            return "极高"
        elif confidence >= 0.8:
            return "高"
        elif confidence >= 0.7:
            return "中等"
        elif confidence >= 0.6:
            return "较低"
        else:
            return "低"

    def _categorize_risk(self, risk_level: RiskLevel) -> str:
        """分类风险等级"""
        risk_mapping = {
            RiskLevel.CRITICAL: "关键风险",
            RiskLevel.HIGH: "高风险",
            RiskLevel.MEDIUM: "中等风险",
            RiskLevel.LOW: "低风险",
            RiskLevel.NEGLIGIBLE: "可忽略风险",
        }
        return risk_mapping.get(risk_level, "未知风险")

    def _get_language(self, file_path: str) -> str:
        """获取文件语言"""
        extension = Path(file_path).suffix.lower()

        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
            ".cpp": "cpp",
            ".c": "c",
            ".cs": "csharp",
            ".php": "php",
            ".rb": "ruby",
            ".rs": "rust",
        }

        return language_map.get(extension, "text")

    def format_multiple_suggestions(
        self,
        suggestions: List[AIFixSuggestion],
        quality_assessments: Optional[List[FixSuggestionQualityAssessment]] = None,
    ) -> List[SuggestionDisplayData]:
        """
        批量格式化多个修复建议

        Args:
            suggestions: AI修复建议列表
            quality_assessments: 质量评估结果列表

        Returns:
            格式化的展示数据列表
        """
        formatted_suggestions = []

        # 如果没有提供质量评估，创建空列表
        if quality_assessments is None:
            quality_assessments = [None] * len(suggestions)

        for suggestion, quality in zip(suggestions, quality_assessments):
            try:
                display_data = self.format_suggestion(suggestion, quality)
                formatted_suggestions.append(display_data)
            except Exception as e:
                logger.error(f"格式化修复建议 {suggestion.suggestion_id} 失败: {e}")
                continue

        logger.info(
            f"批量格式化完成，成功: {len(formatted_suggestions)}/{len(suggestions)}"
        )
        return formatted_suggestions

    def export_to_dict(self, display_data: SuggestionDisplayData) -> Dict[str, Any]:
        """导出展示数据为字典"""
        return asdict(display_data)

    def export_to_json(
        self, display_data: SuggestionDisplayData, indent: int = 2
    ) -> str:
        """导出展示数据为JSON字符串"""
        return json.dumps(
            self.export_to_dict(display_data), ensure_ascii=False, indent=indent
        )
