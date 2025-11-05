"""
T011.2: 用户修改建议处理器

节点E的辅助组件，专门处理用户对修复建议的修改。支持用户修改代码、调整解释、
添加条件等，并验证修改的合理性和可行性。

工作流位置: 节点E (用户决策) - 修改处理
输入: 用户修改请求 + 原始修复建议
输出: 修改后的修复建议 + 修改验证结果
"""

import json
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from ..utils.logger import get_logger
from ..utils.types import FixType, ProblemType, RiskLevel
from .fix_suggestion_displayer import SuggestionDisplayData
from .workflow_data_types import (
    AIFixSuggestion,
    UserInteractionData,
    WorkflowDataPacket,
)
from .workflow_flow_state_manager import WorkflowNode
from .workflow_user_interaction_types import (
    DecisionRationale,
    DecisionType,
    ModificationRequest,
    ModificationResult,
    ModificationType,
    UserAction,
    UserDecision,
)

logger = get_logger()


class ModificationScope(Enum):
    """修改范围枚举"""

    CODE_ONLY = "code_only"  # 仅修改代码
    EXPLANATION_ONLY = "explanation_only"  # 仅修改解释
    BOTH = "both"  # 代码和解释都修改
    METADATA = "metadata"  # 修改元数据
    ALTERNATIVES = "alternatives"  # 修改替代方案


class ModificationValidationResult(Enum):
    """修改验证结果"""

    VALID = "valid"  # 修改有效
    INVALID_SYNTAX = "invalid_syntax"  # 语法错误
    INVALID_LOGIC = "invalid_logic"  # 逻辑错误
    INCOMPLETE = "incomplete"  # 修改不完整
    REGRESSION = "regression"  # 引入回归问题
    NEEDS_REVIEW = "needs_review"  # 需要进一步审查


@dataclass
class UserModificationInput:
    """用户修改输入"""

    original_suggestion_id: str
    modification_type: ModificationType
    modified_code: Optional[str] = None
    modified_explanation: Optional[str] = None
    modified_reasoning: Optional[str] = None
    added_alternatives: List[Dict[str, Any]] = None
    modification_comment: str = ""
    expected_impact: str = ""
    validation_requirements: List[str] = None

    def __post_init__(self):
        if self.added_alternatives is None:
            self.added_alternatives = []
        if self.validation_requirements is None:
            self.validation_requirements = []


@dataclass
class ModificationAnalysis:
    """修改分析结果"""

    scope: ModificationScope
    complexity: str  # simple, moderate, complex
    risk_level: RiskLevel
    estimated_impact: str
    syntax_validation: ModificationValidationResult
    logic_validation: ModificationValidationResult
    completeness_validation: ModificationValidationResult
    changes_summary: str
    potential_side_effects: List[str]
    additional_testing_required: List[str]


@dataclass
class ModifiedSuggestion:
    """修改后的修复建议"""

    suggestion_id: str
    original_suggestion_id: str
    file_path: str
    line_number: int
    modified_code: str
    original_code: str
    modified_explanation: str
    modified_reasoning: str
    confidence: float
    risk_level: RiskLevel
    fix_type: FixType
    side_effects: List[str]
    alternatives: List[Dict[str, Any]]
    testing_requirements: List[str]
    modification_metadata: Dict[str, Any]


@dataclass
class ModificationProcessingResult:
    """修改处理结果"""

    modification_id: str
    original_suggestion_id: str
    success: bool
    modified_suggestion: Optional[ModifiedSuggestion]
    analysis: ModificationAnalysis
    validation_errors: List[str]
    warnings: List[str]
    recommendations: List[str]
    processing_time_seconds: int
    timestamp: datetime


class UserModificationProcessor:
    """用户修改建议处理器"""

    def __init__(self):
        """初始化修改处理器"""
        self._modification_history: List[ModificationProcessingResult] = []
        self._syntax_validators = self._init_syntax_validators()

    def process_modification(
        self,
        modification_input: UserModificationInput,
        original_suggestion: AIFixSuggestion,
    ) -> ModificationProcessingResult:
        """
        处理用户修改请求

        Args:
            modification_input: 用户修改输入
            original_suggestion: 原始修复建议

        Returns:
            修改处理结果
        """
        modification_id = str(uuid.uuid4())
        start_time = datetime.now()

        try:
            logger.info(f"处理用户修改: {modification_id}")

            # 分析修改范围和复杂度
            analysis = self._analyze_modification(
                modification_input, original_suggestion
            )

            # 验证修改
            validation_errors, warnings = self._validate_modification(
                modification_input, original_suggestion, analysis
            )

            # 生成修改后的建议
            modified_suggestion = None
            if not validation_errors:
                modified_suggestion = self._create_modified_suggestion(
                    modification_input, original_suggestion, analysis
                )

            # 生成建议
            recommendations = self._generate_recommendations(
                analysis, validation_errors
            )

            processing_time = int((datetime.now() - start_time).total_seconds())

            result = ModificationProcessingResult(
                modification_id=modification_id,
                original_suggestion_id=modification_input.original_suggestion_id,
                success=len(validation_errors) == 0,
                modified_suggestion=modified_suggestion,
                analysis=analysis,
                validation_errors=validation_errors,
                warnings=warnings,
                recommendations=recommendations,
                processing_time_seconds=processing_time,
                timestamp=datetime.now(),
            )

            # 记录修改历史
            self._record_modification(result)

            logger.info(f"用户修改处理完成: {modification_id}, 成功: {result.success}")
            return result

        except Exception as e:
            logger.error(f"处理用户修改失败: {e}")
            raise

    def batch_process_modifications(
        self,
        modifications: List[UserModificationInput],
        original_suggestions: List[AIFixSuggestion],
    ) -> List[ModificationProcessingResult]:
        """
        批量处理用户修改

        Args:
            modifications: 修改输入列表
            original_suggestions: 原始建议列表

        Returns:
            批量处理结果
        """
        results = []
        logger.info(f"开始批量处理 {len(modifications)} 个修改")

        for modification_input, original_suggestion in zip(
            modifications, original_suggestions
        ):
            try:
                result = self.process_modification(
                    modification_input, original_suggestion
                )
                results.append(result)
            except Exception as e:
                logger.error(f"批量处理修改失败: {e}")
                # 创建失败结果
                failed_result = ModificationProcessingResult(
                    modification_id=str(uuid.uuid4()),
                    original_suggestion_id=modification_input.original_suggestion_id,
                    success=False,
                    modified_suggestion=None,
                    analysis=self._create_failed_analysis(),
                    validation_errors=[str(e)],
                    warnings=[],
                    recommendations=[],
                    processing_time_seconds=0,
                    timestamp=datetime.now(),
                )
                results.append(failed_result)

        successful_count = sum(1 for r in results if r.success)
        logger.info(f"批量修改处理完成: 成功 {successful_count}/{len(results)}")

        return results

    def suggest_modifications(
        self, suggestion: AIFixSuggestion, common_issues: List[str] = None
    ) -> List[ModificationRequest]:
        """
        建议常见修改

        Args:
            suggestion: 修复建议
            common_issues: 常见问题列表

        Returns:
            建议的修改列表
        """
        suggestions = []

        # 分析常见问题并建议修改
        if common_issues is None:
            common_issues = self._identify_common_issues(suggestion)

        for issue in common_issues:
            modification_request = self._create_modification_suggestion(
                suggestion, issue
            )
            if modification_request:
                suggestions.append(modification_request)

        logger.info(f"生成 {len(suggestions)} 个修改建议")
        return suggestions

    def get_modification_history(
        self, limit: Optional[int] = None
    ) -> List[ModificationProcessingResult]:
        """
        获取修改历史

        Args:
            limit: 限制数量

        Returns:
            修改历史列表
        """
        history = self._modification_history.copy()
        history.sort(key=lambda x: x.timestamp, reverse=True)

        if limit:
            history = history[:limit]

        return history

    def _analyze_modification(
        self,
        modification_input: UserModificationInput,
        original_suggestion: AIFixSuggestion,
    ) -> ModificationAnalysis:
        """分析修改"""
        # 确定修改范围
        scope = self._determine_modification_scope(modification_input)

        # 评估复杂度
        complexity = self._assess_complexity(modification_input, original_suggestion)

        # 评估风险等级
        risk_level = self._assess_risk_level(modification_input, original_suggestion)

        # 估算影响
        estimated_impact = self._estimate_impact(
            modification_input, original_suggestion
        )

        # 语法验证
        syntax_validation = self._validate_syntax(
            modification_input, original_suggestion
        )

        # 逻辑验证
        logic_validation = self._validate_logic(modification_input, original_suggestion)

        # 完整性验证
        completeness_validation = self._validate_completeness(modification_input)

        # 生成变更摘要
        changes_summary = self._generate_changes_summary(
            modification_input, original_suggestion
        )

        # 识别潜在副作用
        potential_side_effects = self._identify_side_effects(
            modification_input, original_suggestion
        )

        # 确定额外测试要求
        additional_testing_required = self._determine_additional_testing(
            modification_input, scope, risk_level
        )

        return ModificationAnalysis(
            scope=scope,
            complexity=complexity,
            risk_level=risk_level,
            estimated_impact=estimated_impact,
            syntax_validation=syntax_validation,
            logic_validation=logic_validation,
            completeness_validation=completeness_validation,
            changes_summary=changes_summary,
            potential_side_effects=potential_side_effects,
            additional_testing_required=additional_testing_required,
        )

    def _determine_modification_scope(
        self, modification_input: UserModificationInput
    ) -> ModificationScope:
        """确定修改范围"""
        has_code_modification = bool(modification_input.modified_code)
        has_explanation_modification = bool(modification_input.modified_explanation)
        has_metadata_modification = bool(modification_input.added_alternatives)

        if has_code_modification and has_explanation_modification:
            return ModificationScope.BOTH
        elif has_code_modification:
            return ModificationScope.CODE_ONLY
        elif has_explanation_modification:
            return ModificationScope.EXPLANATION_ONLY
        elif has_metadata_modification:
            return ModificationScope.ALTERNATIVES
        else:
            return ModificationScope.METADATA

    def _assess_complexity(
        self,
        modification_input: UserModificationInput,
        original_suggestion: AIFixSuggestion,
    ) -> str:
        """评估修改复杂度"""
        complexity_score = 0

        # 代码修改复杂度
        if modification_input.modified_code:
            original_lines = len(original_suggestion.suggested_code.splitlines())
            modified_lines = len(modification_input.modified_code.splitlines())
            line_diff = abs(modified_lines - original_lines)

            if line_diff > 10:
                complexity_score += 3
            elif line_diff > 5:
                complexity_score += 2
            elif line_diff > 0:
                complexity_score += 1

            # 检查关键字修改
            if any(
                keyword in modification_input.modified_code.lower()
                for keyword in [
                    "import",
                    "class",
                    "def",
                    "function",
                    "if",
                    "for",
                    "while",
                ]
            ):
                complexity_score += 1

        # 解释修改复杂度
        if modification_input.modified_explanation:
            explanation_diff = len(modification_input.modified_explanation) - len(
                original_suggestion.explanation
            )
            if abs(explanation_diff) > 100:
                complexity_score += 1

        # 替代方案复杂度
        if modification_input.added_alternatives:
            complexity_score += len(modification_input.added_alternatives)

        if complexity_score >= 4:
            return "complex"
        elif complexity_score >= 2:
            return "moderate"
        else:
            return "simple"

    def _assess_risk_level(
        self,
        modification_input: UserModificationInput,
        original_suggestion: AIFixSuggestion,
    ) -> RiskLevel:
        """评估风险等级"""
        risk_score = 0

        # 基于复杂度评估风险
        complexity = self._assess_complexity(modification_input, original_suggestion)
        if complexity == "complex":
            risk_score += 2
        elif complexity == "moderate":
            risk_score += 1

        # 基于修改类型评估风险
        if modification_input.modified_code:
            risk_score += 1

        # 基于问题类型评估风险
        if original_suggestion.problem_type == ProblemType.SECURITY:
            risk_score += 2
        elif original_suggestion.problem_type == ProblemType.PERFORMANCE:
            risk_score += 1

        # 基于原风险等级评估风险
        original_risk_values = {
            RiskLevel.NEGLIGIBLE: 0,
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4,
        }
        risk_score += original_risk_values.get(original_suggestion.risk_level, 2)

        if risk_score >= 5:
            return RiskLevel.CRITICAL
        elif risk_score >= 4:
            return RiskLevel.HIGH
        elif risk_score >= 2:
            return RiskLevel.MEDIUM
        elif risk_score >= 1:
            return RiskLevel.LOW
        else:
            return RiskLevel.NEGLIGIBLE

    def _estimate_impact(
        self,
        modification_input: UserModificationInput,
        original_suggestion: AIFixSuggestion,
    ) -> str:
        """估算影响"""
        scope = self._determine_modification_scope(modification_input)
        complexity = self._assess_complexity(modification_input, original_suggestion)

        if scope == ModificationScope.BOTH and complexity == "complex":
            return "重大影响：可能影响系统架构和多个功能模块"
        elif scope == ModificationScope.CODE_ONLY and complexity in [
            "complex",
            "moderate",
        ]:
            return "较大影响：可能影响相关功能和性能"
        elif scope == ModificationScope.CODE_ONLY and complexity == "simple":
            return "中等影响：主要影响当前修复功能"
        elif scope == ModificationScope.EXPLANATION_ONLY:
            return "轻微影响：仅影响理解和文档"
        else:
            return "影响较小：主要是元数据更新"

    def _validate_syntax(
        self,
        modification_input: UserModificationInput,
        original_suggestion: AIFixSuggestion,
    ) -> ModificationValidationResult:
        """验证语法"""
        if not modification_input.modified_code:
            return ModificationValidationResult.VALID

        # 获取文件语言
        language = self._get_file_language(original_suggestion.file_path)

        # 使用相应的语法验证器
        if language in self._syntax_validators:
            validator = self._syntax_validators[language]
            try:
                is_valid = validator(modification_input.modified_code)
                return (
                    ModificationValidationResult.VALID
                    if is_valid
                    else ModificationValidationResult.INVALID_SYNTAX
                )
            except Exception:
                return ModificationValidationResult.INVALID_SYNTAX

        # 简单的语法检查
        return self._basic_syntax_check(modification_input.modified_code, language)

    def _validate_logic(
        self,
        modification_input: UserModificationInput,
        original_suggestion: AIFixSuggestion,
    ) -> ModificationValidationResult:
        """验证逻辑"""
        # 基本逻辑检查
        if modification_input.modified_code:
            # 检查是否引入明显的逻辑问题
            if self._has_logic_issues(modification_input.modified_code):
                return ModificationValidationResult.INVALID_LOGIC

            # 检查是否与原始问题匹配
            if not self._matches_problem_context(
                modification_input.modified_code, original_suggestion
            ):
                return ModificationValidationResult.NEEDS_REVIEW

        return ModificationValidationResult.VALID

    def _validate_completeness(
        self, modification_input: UserModificationInput
    ) -> ModificationValidationResult:
        """验证完整性"""
        if modification_input.modification_type == ModificationType.ALTERNATIVE:
            if not modification_input.added_alternatives:
                return ModificationValidationResult.INCOMPLETE

        if (
            modification_input.modified_code
            and not modification_input.modified_explanation
        ):
            return ModificationValidationResult.NEEDS_REVIEW

        return ModificationValidationResult.VALID

    def _validate_modification(
        self,
        modification_input: UserModificationInput,
        original_suggestion: AIFixSuggestion,
        analysis: ModificationAnalysis,
    ) -> Tuple[List[str], List[str]]:
        """验证修改"""
        errors = []
        warnings = []

        # 语法验证
        if analysis.syntax_validation != ModificationValidationResult.VALID:
            errors.append("修改的代码存在语法错误")

        # 逻辑验证
        if analysis.logic_validation == ModificationValidationResult.INVALID_LOGIC:
            errors.append("修改引入了逻辑错误")
        elif analysis.logic_validation == ModificationValidationResult.NEEDS_REVIEW:
            warnings.append("修改可能存在逻辑问题，建议仔细审查")

        # 完整性验证
        if analysis.completeness_validation == ModificationValidationResult.INCOMPLETE:
            errors.append("修改不完整，缺少必要信息")

        # 风险警告
        if analysis.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            warnings.append(f"修改风险等级为{analysis.risk_level.value}，建议充分测试")

        # 复杂度警告
        if analysis.complexity == "complex":
            warnings.append("修改较为复杂，建议分步实施")

        return errors, warnings

    def _create_modified_suggestion(
        self,
        modification_input: UserModificationInput,
        original_suggestion: AIFixSuggestion,
        analysis: ModificationAnalysis,
    ) -> ModifiedSuggestion:
        """创建修改后的建议"""
        modified_suggestion = ModifiedSuggestion(
            suggestion_id=str(uuid.uuid4()),
            original_suggestion_id=original_suggestion.suggestion_id,
            file_path=original_suggestion.file_path,
            line_number=original_suggestion.line_number,
            modified_code=modification_input.modified_code
            or original_suggestion.suggested_code,
            original_code=original_suggestion.original_code,
            modified_explanation=modification_input.modified_explanation
            or original_suggestion.explanation,
            modified_reasoning=modification_input.modified_reasoning
            or original_suggestion.reasoning,
            confidence=max(
                0.1, original_suggestion.confidence - 0.1
            ),  # 修改后置信度略微降低
            risk_level=analysis.risk_level,
            fix_type=original_suggestion.fix_type,
            side_effects=analysis.potential_side_effects,
            alternatives=modification_input.added_alternatives
            or original_suggestion.alternatives,
            testing_requirements=analysis.additional_testing_required,
            modification_metadata={
                "modification_id": str(uuid.uuid4()),
                "modification_type": modification_input.modification_type.value,
                "modification_comment": modification_input.modification_comment,
                "expected_impact": modification_input.expected_impact,
                "complexity": analysis.complexity,
                "scope": analysis.scope.value,
                "timestamp": datetime.now().isoformat(),
            },
        )

        return modified_suggestion

    def _generate_changes_summary(
        self,
        modification_input: UserModificationInput,
        original_suggestion: AIFixSuggestion,
    ) -> str:
        """生成变更摘要"""
        changes = []

        if modification_input.modified_code:
            original_lines = len(original_suggestion.suggested_code.splitlines())
            modified_lines = len(modification_input.modified_code.splitlines())
            changes.append(f"代码修改：{original_lines} → {modified_lines} 行")

        if modification_input.modified_explanation:
            changes.append("解释说明已更新")

        if modification_input.added_alternatives:
            changes.append(
                f"新增 {len(modification_input.added_alternatives)} 个替代方案"
            )

        if modification_input.modified_reasoning:
            changes.append("推理过程已更新")

        return "；".join(changes) if changes else "无明显变更"

    def _identify_side_effects(
        self,
        modification_input: UserModificationInput,
        original_suggestion: AIFixSuggestion,
    ) -> List[str]:
        """识别潜在副作用"""
        side_effects = []

        if modification_input.modified_code:
            code = modification_input.modified_code.lower()

            # 检查可能的影响
            if "import" in code:
                side_effects.append("可能影响模块依赖关系")

            if "global" in code or "static" in code:
                side_effects.append("可能影响全局状态")

            if "database" in code or "db" in code or "sql" in code:
                side_effects.append("可能影响数据库操作")

            if "network" in code or "http" in code or "api" in code:
                side_effects.append("可能影响网络通信")

            if "thread" in code or "async" in code or "await" in code:
                side_effects.append("可能影响并发行为")

        return side_effects

    def _determine_additional_testing(
        self,
        modification_input: UserModificationInput,
        scope: ModificationScope,
        risk_level: RiskLevel,
    ) -> List[str]:
        """确定额外测试要求"""
        testing_requirements = []

        if scope in [ModificationScope.CODE_ONLY, ModificationScope.BOTH]:
            testing_requirements.extend(
                ["单元测试验证", "功能回归测试", "代码语法检查"]
            )

        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            testing_requirements.extend(["集成测试", "性能测试", "安全性测试"])

        if modification_input.modified_code:
            testing_requirements.append("静态代码分析")

        return testing_requirements

    def _generate_recommendations(
        self, analysis: ModificationAnalysis, validation_errors: List[str]
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        if validation_errors:
            recommendations.append("请修复验证错误后重新提交")

        if analysis.complexity == "complex":
            recommendations.append("建议将复杂修改分解为多个简单修改")

        if analysis.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            recommendations.append("建议在测试环境中充分验证后再应用")

        if analysis.scope == ModificationScope.BOTH:
            recommendations.append("建议确保代码修改与解释说明保持一致")

        if not recommendations:
            recommendations.append("修改看起来合理，可以继续处理")

        return recommendations

    def _init_syntax_validators(self) -> Dict[str, callable]:
        """初始化语法验证器"""
        validators = {}

        try:
            # Python语法验证
            import ast

            validators["python"] = lambda code: self._validate_python_syntax(code)
        except ImportError:
            pass

        try:
            # JavaScript语法验证
            import esprima

            validators["javascript"] = lambda code: self._validate_javascript_syntax(
                code
            )
        except ImportError:
            pass

        return validators

    def _validate_python_syntax(self, code: str) -> bool:
        """验证Python语法"""
        try:
            import ast

            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def _validate_javascript_syntax(self, code: str) -> bool:
        """验证JavaScript语法"""
        try:
            import esprima

            esprima.parse(code)
            return True
        except:
            return False

    def _basic_syntax_check(
        self, code: str, language: str
    ) -> ModificationValidationResult:
        """基本语法检查"""
        # 简单的语法检查规则
        if language == "python":
            # 检查括号匹配
            if code.count("(") != code.count(")"):
                return ModificationValidationResult.INVALID_SYNTAX
            if code.count("[") != code.count("]"):
                return ModificationValidationResult.INVALID_SYNTAX
            if code.count("{") != code.count("}"):
                return ModificationValidationResult.INVALID_SYNTAX

        # 检查基本结构
        lines = code.strip().split("\n")
        for line in lines:
            if line.strip() and not line.strip().startswith("#"):
                # 基本的代码行检查
                if not re.match(
                    r'^[\s\w\(\)\[\]\{\}\+\-\*/\=\<\>\!\&\|\:\;\,\.\'"]+$', line
                ):
                    # 包含可疑字符，但可能有效
                    pass

        return ModificationValidationResult.VALID

    def _has_logic_issues(self, code: str) -> bool:
        """检查逻辑问题"""
        code_lower = code.lower()

        # 检查常见逻辑问题
        logic_issues = [
            "while true",  # 无限循环
            "if true:",  # 总是真的条件
            "if false:",  # 总是假的条件
            "return none",  # 总是返回None
            "pass",  # 空实现
        ]

        return any(issue in code_lower for issue in logic_issues)

    def _matches_problem_context(
        self, code: str, original_suggestion: AIFixSuggestion
    ) -> bool:
        """检查是否匹配问题上下文"""
        # 简单的上下文匹配检查
        if not code:
            return False

        # 检查代码长度是否合理
        if len(code.splitlines()) > 100:  # 过长的代码可能有问题
            return False

        # 检查是否包含相关关键词
        problem_keywords = str(original_suggestion.problem_type.value).lower()
        code_lower = code.lower()

        # 如果是安全问题，应该包含安全相关代码
        if "security" in problem_keywords or "安全" in problem_keywords:
            security_keywords = ["validate", "check", "secure", "safe", "验证", "检查"]
            return any(keyword in code_lower for keyword in security_keywords)

        return True

    def _get_file_language(self, file_path: str) -> str:
        """获取文件语言"""
        from pathlib import Path

        extension = Path(file_path).suffix.lower()

        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".go": "go",
            ".cpp": "cpp",
            ".c": "c",
        }

        return language_map.get(extension, "text")

    def _identify_common_issues(self, suggestion: AIFixSuggestion) -> List[str]:
        """识别常见问题"""
        issues = []

        code = suggestion.suggested_code.lower()

        if "TODO" in code or "FIXME" in code:
            issues.append("包含未完成的标记")

        if len(code.splitlines()) > 50:
            issues.append("代码过长，可能需要简化")

        if suggestion.confidence < 0.7:
            issues.append("置信度较低，建议改进")

        if not suggestion.explanation or len(suggestion.explanation) < 20:
            issues.append("解释过于简单，需要补充")

        return issues

    def _create_modification_suggestion(
        self, suggestion: AIFixSuggestion, issue: str
    ) -> Optional[ModificationRequest]:
        """创建修改建议"""
        if "未完成的标记" in issue:
            return ModificationRequest(
                request_id=str(uuid.uuid4()),
                suggestion_id=suggestion.suggestion_id,
                modification_type=ModificationType.EXPLANATION,
                suggested_changes={
                    "explanation": "请补充完整的实现说明，移除TODO和FIXME标记"
                },
                reason="建议提供完整的修复方案",
                priority="medium",
            )
        elif "代码过长" in issue:
            return ModificationRequest(
                request_id=str(uuid.uuid4()),
                suggestion_id=suggestion.suggestion_id,
                modification_type=ModificationType.CODE_REFACTOR,
                suggested_changes={"code": "建议将长代码拆分为多个函数或类"},
                reason="提高代码可读性和可维护性",
                priority="low",
            )
        elif "置信度较低" in issue:
            return ModificationRequest(
                request_id=str(uuid.uuid4()),
                suggestion_id=suggestion.suggestion_id,
                modification_type=ModificationType.IMPROVE_CONFIDENCE,
                suggested_changes={"reasoning": "建议提供更详细的推理过程"},
                reason="提高建议的可信度",
                priority="high",
            )

        return None

    def _create_failed_analysis(self) -> ModificationAnalysis:
        """创建失败分析结果"""
        return ModificationAnalysis(
            scope=ModificationScope.METADATA,
            complexity="simple",
            risk_level=RiskLevel.LOW,
            estimated_impact="无影响",
            syntax_validation=ModificationValidationResult.NEEDS_REVIEW,
            logic_validation=ModificationValidationResult.NEEDS_REVIEW,
            completeness_validation=ModificationValidationResult.INCOMPLETE,
            changes_summary="处理失败",
            potential_side_effects=[],
            additional_testing_required=[],
        )

    def _record_modification(self, result: ModificationProcessingResult) -> None:
        """记录修改"""
        self._modification_history.append(result)

        # 限制历史记录数量
        if len(self._modification_history) > 500:
            self._modification_history = self._modification_history[-250:]

    def export_modification_history(self, limit: Optional[int] = None) -> str:
        """导出修改历史"""
        history = self.get_modification_history(limit)

        exportable_history = []
        for record in history:
            record_dict = asdict(record)
            record_dict["timestamp"] = record.timestamp.isoformat()
            if record.modified_suggestion:
                record_dict["modified_suggestion"] = asdict(record.modified_suggestion)
            record_dict["analysis"] = asdict(record.analysis)
            exportable_history.append(record_dict)

        return json.dumps(exportable_history, ensure_ascii=False, indent=2)
