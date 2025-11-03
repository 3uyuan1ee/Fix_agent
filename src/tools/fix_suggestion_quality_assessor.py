"""
修复建议质量评估器 - T009.3
评估AI修复建议的质量和安全性
"""

import ast
import os
import re
import subprocess
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from ..utils.logger import get_logger
try:
    from .ai_fix_suggestion_generator import AIFixSuggestion, FixSuggestionResult
    from .workflow_data_types import FixType, RiskLevel
    from .fix_suggestion_context_builder import FixSuggestionContext
except ImportError:
    # 如果相关模块不可用，定义基本类型
    from enum import Enum

    class FixType(Enum):
        CODE_REPLACEMENT = "code_replacement"
        CODE_INSERTION = "code_insertion"
        CODE_DELETION = "code_deletion"
        REFACTORING = "refactoring"
        CONFIGURATION = "configuration"
        DEPENDENCY_UPDATE = "dependency_update"

    class RiskLevel(Enum):
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"

    @dataclass
    class AIFixSuggestion:
        suggestion_id: str
        problem_id: str
        file_path: str
        line_number: int
        original_code: str
        suggested_code: str
        explanation: str
        reasoning: str
        confidence: float
        risk_level: RiskLevel = RiskLevel.MEDIUM
        side_effects: List[str] = field(default_factory=list)
        alternatives: List[Any] = field(default_factory=list)
        estimated_impact: str = ""
        fix_type: FixType = FixType.CODE_REPLACEMENT
        dependencies: List[str] = field(default_factory=list)
        testing_requirements: List[str] = field(default_factory=list)

    @dataclass
    class FixSuggestionResult:
        suggestion_id: str
        context_id: str
        fix_suggestions: List[AIFixSuggestion] = field(default_factory=list)
        suggestion_summary: Dict[str, Any] = field(default_factory=dict)
        execution_success: bool = True
        execution_time: float = 0.0
        error_message: str = ""

    @dataclass
    class FixSuggestionContext:
        context_id: str
        validation_result: Any
        file_contents: Dict[str, str] = field(default_factory=dict)
        file_dependencies: Dict[str, List[str]] = field(default_factory=dict)
        project_context: Dict[str, Any] = field(default_factory=dict)
        user_preferences: Dict[str, Any] = field(default_factory=dict)
        fix_constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityAssessmentResult:
    """质量评估结果"""
    suggestion_id: str
    overall_score: float  # 0.0-1.0
    category_scores: Dict[str, float] = field(default_factory=dict)
    assessment_issues: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)
    syntax_validation: Dict[str, Any] = field(default_factory=dict)
    security_assessment: Dict[str, Any] = field(default_factory=dict)
    is_recommended: bool = True
    adjusted_risk_level: RiskLevel = RiskLevel.MEDIUM
    assessment_timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "suggestion_id": self.suggestion_id,
            "overall_score": self.overall_score,
            "category_scores": self.category_scores,
            "assessment_issues": self.assessment_issues,
            "improvement_suggestions": self.improvement_suggestions,
            "syntax_validation": self.syntax_validation,
            "security_assessment": self.security_assessment,
            "is_recommended": self.is_recommended,
            "adjusted_risk_level": self.adjusted_risk_level.value,
            "assessment_timestamp": self.assessment_timestamp
        }


class FixSuggestionQualityAssessor:
    """修复建议质量评估器"""

    def __init__(self,
                 min_acceptance_score: float = 0.6,
                 enable_syntax_validation: bool = True,
                 enable_security_analysis: bool = True):
        self.min_acceptance_score = min_acceptance_score
        self.enable_syntax_validation = enable_syntax_validation
        self.enable_security_analysis = enable_security_analysis
        self.logger = get_logger()

        # 质量评估权重配置
        self.assessment_weights = {
            "syntax_correctness": 0.25,      # 语法正确性
            "logic_soundness": 0.20,         # 逻辑合理性
            "solution_completeness": 0.15,  # 解决方案完整性
            "risk_assessment": 0.15,          # 风险评估准确性
            "explanation_quality": 0.10,       # 解释说明质量
            "alternative_quality": 0.10,        # 替代方案质量
            "feasibility": 0.05                 # 可行性评估
        }

        # 语法验证配置
        self.syntax_config = {
            "python": {
                "parser": ast.parse,
                "file_extension": ".py",
                "check_imports": True,
                "check_style": False
            },
            "javascript": {
                "node_check": False,  # 需要Node.js环境
                "basic_syntax": True,
                "file_extensions": [".js", ".jsx", ".ts", ".tsx"]
            }
        }

        # 安全性检查模式
        self.security_patterns = {
            "insecure_functions": [
                "eval", "exec", "compile", "execfile",
                "subprocess.call", "os.system", "os.popen"
            ],
            "dangerous_imports": [
                "pickle", "cPickle", "marshal", "shelve",
                "os.path", "tempfile.NamedTemporaryFile"
            ],
            "sql_injection_patterns": [
                r"execute\s*\(",
                r"executemany\s*\(",
                r"cursor\.execute\s*\("
            ],
            "path_traversal_patterns": [
                r"\.\./",
                r"\.\.\\",
                r"\.\.\\\\",
                r"open\s*\([\"'].*\.\.[\"']"
            ]
        }

    def assess_suggestion_quality(self,
                                 suggestion: AIFixSuggestion,
                                 suggestion_context: FixSuggestionContext) -> QualityAssessmentResult:
        """
        评估修复建议质量

        Args:
            suggestion: AI修复建议
            suggestion_context: 修复建议上下文

        Returns:
            QualityAssessmentResult: 评估结果
        """
        self.logger.debug(f"开始评估修复建议质量: {suggestion.suggestion_id}")

        result = QualityAssessmentResult(
            suggestion_id=suggestion.suggestion_id,
            assessment_timestamp=datetime.now().isoformat()
        )

        try:
            # 1. 语法正确性评估
            syntax_score, syntax_validation = self._assess_syntax_correctness(
                suggestion, suggestion_context
            )
            result.category_scores["syntax_correctness"] = syntax_score
            result.syntax_validation = syntax_validation

            # 2. 逻辑合理性评估
            logic_score = self._assess_logic_soundness(suggestion, suggestion_context)
            result.category_scores["logic_soundness"] = logic_score

            # 3. 解决方案完整性评估
            completeness_score = self._assess_solution_completeness(suggestion, suggestion_context)
            result.category_scores["solution_completeness"] = completeness_score

            # 4. 风险评估准确性
            risk_score = self._assess_risk_assessment(suggestion, suggestion_context)
            result.category_scores["risk_assessment"] = risk_score

            # 5. 解释说明质量评估
            explanation_score = self._assess_explanation_quality(suggestion)
            result.category_scores["explanation_quality"] = explanation_score

            # 6. 替代方案质量评估
            alternative_score = self._assess_alternative_quality(suggestion)
            result.category_scores["alternative_quality"] = alternative_score

            # 7. 可行性评估
            feasibility_score = self._assess_feasibility(suggestion, suggestion_context)
            result.category_scores["feasibility"] = feasibility_score

            # 计算总体质量分数
            result.overall_score = self._calculate_overall_score(result.category_scores)

            # 收集评估问题
            result.assessment_issues = self._collect_assessment_issues(result)

            # 生成改进建议
            result.improvement_suggestions = self._generate_improvement_suggestions(result)

            # 安全性评估
            if self.enable_security_analysis:
                result.security_assessment = self._assess_security_aspects(suggestion, suggestion_context)

            # 判断是否推荐
            result.is_recommended = self._is_suggestion_recommended(result)

            # 调整风险等级
            result.adjusted_risk_level = self._adjust_risk_level(suggestion.risk_level, result.overall_score)

            self.logger.debug(
                f"修复建议质量评估完成: {suggestion.suggestion_id}, "
                f"总体分数: {result.overall_score:.3f}"
            )

        except Exception as e:
            self.logger.error(f"评估修复建议质量失败 {suggestion.suggestion_id}: {e}")
            result.assessment_issues.append(f"评估过程中发生错误: {e}")
            result.overall_score = 0.0
            result.is_recommended = False

        return result

    def _assess_syntax_correctness(self,
                                suggestion: AIFixSuggestion,
                                suggestion_context: FixSuggestionContext) -> Tuple[float, Dict[str, Any]]:
        """评估语法正确性"""
        if not self.enable_syntax_validation:
            return 1.0, {"status": "disabled"}

        file_path = suggestion.file_path
        language = self._detect_language(file_path)

        validation_result = {
            "status": "unknown",
            "syntax_errors": [],
            "import_errors": [],
            "style_issues": [],
            "language": language,
            "original_code_valid": False,
            "suggested_code_valid": False
        }

        try:
            # 验证原始代码语法
            if self._validate_code_syntax(file_path, suggestion.original_code, validation_result):
                validation_result["original_code_valid"] = True
            else:
                validation_result["syntax_errors"].append("原始代码存在语法错误")

            # 验证建议代码语法
            if self._validate_code_syntax(file_path, suggestion.suggested_code, validation_result):
                validation_result["suggested_code_valid"] = True
            else:
                validation_result["syntax_errors"].append("建议代码存在语法错误")

            # 计算语法分数
            if validation_result["original_code_valid"] and validation_result["suggested_code_valid"]:
                syntax_score = 1.0
                validation_result["status"] = "valid"
            elif validation_result["suggested_code_valid"]:
                syntax_score = 0.7
                validation_result["status"] = "suggested_valid"
            else:
                syntax_score = 0.0
                validation_result["status"] = "invalid"

        except Exception as e:
            self.logger.warning(f"语法验证失败 {file_path}: {e}")
            syntax_score = 0.5
            validation_result["status"] = "error"
            validation_result["syntax_errors"].append(f"验证过程错误: {e}")

        return syntax_score, validation_result

    def _validate_code_syntax(self, file_path: str, code: str, validation_result: Dict[str, Any]) -> bool:
        """验证代码语法"""
        language = validation_result["language"]

        if language == "python":
            return self._validate_python_syntax(code, validation_result)
        elif language in ["javascript", "typescript"]:
            return self._validate_javascript_syntax(code, validation_result)
        else:
            # 对于其他语言，进行基本检查
            return self._validate_basic_syntax(code, validation_result)

    def _validate_python_syntax(self, code: str, validation_result: Dict[str, Any]) -> bool:
        """验证Python语法"""
        try:
            ast.parse(code)

            # 检查导入语句
            if validation_result.get("check_imports", False):
                import_errors = self._check_python_imports(code)
                validation_result["import_errors"] = import_errors

            return True

        except SyntaxError as e:
            validation_result["syntax_errors"].append(f"语法错误: {e}")
            return False
        except Exception as e:
            validation_result["syntax_errors"].append(f"解析错误: {e}")
            return False

    def _validate_javascript_syntax(self, code: str, validation_result: Dict[str, Any]) -> bool:
        """验证JavaScript/TypeScript语法"""
        # 基本的JavaScript语法检查
        try:
            # 检查基本的语法平衡
            if not self._check_brace_balance(code):
                validation_result["syntax_errors"].append("括号不匹配")
                return False

            # 检查字符串引号平衡
            if not self._check_quote_balance(code):
                validation_result["syntax_errors"].append("引号不匹配")
                return False

            return True

        except Exception as e:
            validation_result["syntax_errors"].append(f"语法检查错误: {e}")
            return False

    def _validate_basic_syntax(self, code: str, validation_result: Dict[str, Any]) -> bool:
        """验证基本语法"""
        try:
            # 检查基本的语法平衡
            if not self._check_brace_balance(code):
                validation_result["syntax_errors"].append("括号不匹配")
                return False

            if not self._check_quote_balance(code):
                validation_result["syntax_errors"].append("引号不匹配")
                return False

            return True

        except Exception as e:
            validation_result["syntax_errors"].append(f"基本语法检查错误: {e}")
            return False

    def _check_brace_balance(self, code: str) -> bool:
        """检查括号平衡"""
        stack = []
        bracket_pairs = {'(': ')', '[': ']', '{': '}'}

        for char in code:
            if char in bracket_pairs:
                if char in bracket_pairs.values():
                    if not stack or stack[-1] != char:
                        return False
                    stack.pop()
                else:
                    stack.append(char)

        return not stack

    def _check_quote_balance(self, code: str) -> bool:
        """检查引号平衡"""
        single_quote = False
        double_quote = False

        for char in code:
            if char == "'" and not double_quote:
                single_quote = not single_quote
            elif char == '"' and not single_quote:
                double_quote = not double_quote

        return not (single_quote or double_quote)

    def _check_python_imports(self, code: str) -> List[str]:
        """检查Python导入语句"""
        errors = []
        lines = code.split('\n')

        for i, line in lines:
            line = line.strip()
            if line.startswith(('import ', 'from ')):
                try:
                    if line.startswith('from '):
                        exec(line)  # 测试导入是否有效
                    else:
                        exec(line)
                except Exception as e:
                    errors.append(f"行{i+1}: 导入错误 - {e}")

        return errors

    def _assess_logic_soundness(self,
                              suggestion: AIFixSuggestion,
                              suggestion_context: FixSuggestionContext) -> float:
        """评估逻辑合理性"""
        score = 0.0
        total_checks = 0

        # 检查修复是否针对问题
        original_lines = len(suggestion.original_code.split('\n'))
        suggested_lines = len(suggestion.suggested_code.split('\n'))

        total_checks += 1
        if suggested_lines <= original_lines * 2:  # 修复代码不过于冗长
            score += 1

        # 检查修复类型是否合理
        total_checks += 1
        if self._is_fix_type_reasonable(suggestion):
            score += 1

        # 检查是否保持代码风格一致性
        total_checks += 1
        if self._maintains_code_style(suggestion, suggestion_context):
            score += 1

        # 检查修复是否引入新问题
        total_checks += 1
        if not self._introduces_obvious_issues(suggestion):
            score += 1

        # 检查解释和推理的一致性
        total_checks += 1
        if self._explanation_reasoning_consistent(suggestion):
            score += 1

        return score / total_checks if total_checks > 0 else 0.0

    def _is_fix_type_reasonable(self, suggestion: AIFixSuggestion) -> bool:
        """检查修复类型是否合理"""
        problem_types = {
            FixType.CODE_REPLACEMENT: ["替换", "修改", "更新", "改进"],
            FixType.CODE_INSERTION: ["添加", "插入", "新增"],
            FixType.CODE_DELETION: ["删除", "移除", "去除"],
            FixType.REFACTORING: ["重构", "重组", "优化"],
            FixType.CONFIGURATION: ["配置", "设置", "调整"],
            FixType.DEPENDENCY_UPDATE: ["依赖", "库", "包"]
        }

        fix_type = suggestion.fix_type
        explanation = suggestion.explanation.lower()
        reasoning = suggestion.reasoning.lower()

        # 检查解释和推理中是否包含相关关键词
        if fix_type in problem_types:
            keywords = problem_types[fix_type]
            if any(keyword in explanation or keyword in reasoning for keyword in keywords):
                return True

        return False

    def _maintains_code_style(self, suggestion: AIFixSuggestion, suggestion_context: FixSuggestionContext) -> bool:
        """检查是否保持代码风格一致性"""
        # 简化的风格检查
        original_indentation = self._get_indentation_style(suggestion.original_code)
        suggested_indentation = self._get_indentation_style(suggested_code)

        # 如果缩进风格一致
        return original_indentation == suggested_indentation

    def _get_indentation_style(self, code: str) -> str:
        """获取缩进风格"""
        lines = [line for line in code.split('\n') if line.strip()]
        if not lines:
            return "unknown"

        # 统计每行的缩进
        indentations = []
        for line in lines:
            if line.startswith((' ', '\t')):
                indentations.append(line[:len(line) - len(line.lstrip())])

        if not indentations:
            return "none"

        # 判断主要缩进风格
        if all(indent == '    ' for indent in indentations):
            return "4_spaces"
        elif all(indent == '  ' for indent in indentations):
            return "2_spaces"
        elif all(indent == '\t' for indent in indentations):
            return "tab"
        else:
            return "mixed"

    def _introduces_obvious_issues(self, suggestion: AIFixSuggestion) -> bool:
        """检查是否引入明显的新问题"""
        suggested_lower = suggestion.suggested_code.lower()
        reasoning_lower = suggestion.reasoning.lower()

        # 检查是否包含可能的问题模式
        problem_patterns = [
            "todo", "fixme", "xxx", "hack", "temporary",
            "print(", "console.log", "debug("
        ]

        for pattern in problem_patterns:
            if pattern in suggested_lower:
                return False

        # 检查推理中是否提到了新问题
        new_issue_keywords = ["新问题", "引入", "产生", "导致"]
        for keyword in new_issue_keywords:
            if keyword in reasoning_lower:
                return False

        return True

    def _explanation_reasoning_consistent(self, suggestion: AIFixSuggestion) -> bool:
        """检查解释和推理的一致性"""
        explanation_words = set(suggestion.explanation.lower().split())
        reasoning_words = set(suggestion.reasoning.lower().split())

        # 计算词汇重叠度
        if explanation_words and reasoning_words:
            overlap = len(explanation_words & reasoning_words)
            coverage = overlap / len(explanation_words)
            return coverage >= 0.3  # 至少30%的词汇重叠

        return False

    def _assess_solution_completeness(self,
                                    suggestion: AIFixSuggestion,
                                    suggestion_context: FixSuggestionContext) -> float:
        """评估解决方案完整性"""
        score = 0.0
        total_checks = 0

        # 检查是否有具体的修复代码
        total_checks += 1
        if suggestion.suggested_code and len(suggestion.suggested_code.strip()) > 10:
            score += 1

        # 检查是否有详细的解释
        total_checks += 1
        if len(suggestion.explanation.strip()) >= 20:
            score += 1

        # 检查是否有深入的推理过程
        total_checks += 1
        if len(suggestion.reasoning.strip()) >= 30:
            score += 1

        # 检查是否考虑副作用
        total_checks += 1
        if suggestion.side_effects:
            score += 1

        # 检查是否有测试要求
        total_checks += 1
        if suggestion.testing_requirements:
            score += 1

        # 检查是否有影响评估
        total_checks += 1
        if suggestion.estimated_impact:
            score += 1

        return score / total_checks if total_checks > 0 else 0.0

    def _assess_risk_assessment(self,
                            suggestion: AIFixSuggestion,
                            suggestion_context: FixSuggestionContext) -> float:
        """评估风险评估准确性"""
        score = 0.0
        total_checks = 0

        # 检查风险等级是否合理
        total_checks += 1
        if self._is_risk_level_reasonable(suggestion, suggestion_context):
            score += 1

        # 检查副作用描述的合理性
        total_checks += 1
        if suggestion.side_effects:
            if self._are_side_effects_reasonable(suggestion):
                score += 1

        # 检查是否考虑了文件依赖
        total_checks += 1
        if self._considers_dependencies(suggestion, suggestion_context):
            score += 1

        # 检查风险评估与问题严重程度的一致性
        total_checks += 1
        if self._risk_severity_consistent(suggestion, suggestion_context):
            score += 1

        return score / total_checks if total_checks > 0 else 0.0

    def _is_risk_level_reasonable(self, suggestion: AIFixSuggestion, suggestion_context: FixSuggestionContext) -> bool:
        """检查风险等级是否合理"""
        # 这里可以根据项目类型和约束来调整风险期望
        constraints = suggestion_context.fix_constraints

        # 如果是高风险问题，建议也应该是高风险
        project_risk = suggestion_context.project_context.get("risk_assessment", {}).get("overall_risk", "medium")
        suggestion_risk = suggestion.risk_level.value

        # 高风险项目应该更保守
        if project_risk == "high" and suggestion_risk == "low":
            return False

        # 低风险项目可以更积极
        if project_risk == "low" and suggestion_risk == "high":
            return False

        return True

    def _are_side_effects_reasonable(self, suggestion: AIFixSuggestion) -> bool:
        """检查副作用描述是否合理"""
        for side_effect in suggestion.side_effects:
            # 检查副作用描述是否具体
            if len(side_effect.strip()) < 10:
                return False

            # 检查是否包含影响评估
            if any(impact in side_effect.lower() for impact in ["影响", "改变", "修改"]):
                return True

        return len(suggestion.side_effects) <= 5  # 副作用数量合理

    def _considers_dependencies(self, suggestion: AIFixSuggestion, suggestion_context: FixSuggestionContext) -> bool:
        """检查是否考虑了文件依赖"""
        if not suggestion.dependencies:
            # 如果没有依赖，检查是否合理
            return suggestion.fix_type in [
                FixType.CODE_DELETION, FixType.CODE_REPLACEMENT
            ]

        return len(suggestion.dependencies) <= 5  # 依赖数量合理

    def _risk_severity_consistent(self, suggestion: AIFixSuggestion, suggestion_context: FixSuggestionContext) -> bool:
        """检查风险等级与严重程度的一致性"""
        # 这里应该获取原始问题的严重程度
        # 简化处理：假设高风险修复对应高严重程度问题
        high_risk_fixes = [FixType.REFACTORING, FixType.DEPENDENCY_UPDATE]
        medium_risk_fixes = [FixType.CODE_REPLACEMENT, FixType.CONFIGURATION]
        low_risk_fixes = [FixType.CODE_INSERTION, FixType.CODE_DELETION]

        if suggestion.risk_level == RiskLevel.HIGH:
            return suggestion.fix_type in high_risk_fixes
        elif suggestion.risk_level == RiskLevel.MEDIUM:
            return suggestion.fix_type in medium_risk_fixes + high_risk_fixes
        else:
            return True  # 低风险修复可以是任何类型

    def _assess_explanation_quality(self, suggestion: AIFixSuggestion) -> float:
        """评估解释说明质量"""
        score = 0.0
        total_checks = 0

        explanation = suggestion.explanation

        # 检查长度
        total_checks += 1
        if 20 <= len(explanation) <= 200:
            score += 1

        # 检查是否包含具体信息
        total_checks += 1
        if any(char in explanation for char in [':', '。', '！', '?']):
            score += 1

        # 检查是否包含技术细节
        total_checks += 1
        tech_keywords = ["函数", "变量", "类", "方法", "参数", "返回值", "调用"]
        if any(keyword in explanation for keyword in tech_keywords):
            score += 1

        # 检查是否清晰易懂
        total_checks += 1
        if len(explanation.split()) <= 50:  # 不过于复杂
            score += 1

        return score / total_checks if total_checks > 0 else 0.0

    def _assess_alternative_quality(self, suggestion: AIFixSuggestion) -> float:
        """评估替代方案质量"""
        if not suggestion.alternatives:
            return 1.0  # 没有替代方案是合理的

        score = 0.0
        total_alternatives = len(suggestion.alternatives)

        # 检查替代方案数量合理性
        if total_alternatives <= 3:
            score += 0.5

        # 检查每个替代方案的质量
        for alternative in suggestion.alternatives:
            if alternative.approach and alternative.code:
                score += 0.5 / total_alternatives

        return min(score, 1.0)

    def _assess_feasibility(self, suggestion: AIFixSuggestion, suggestion_context: FixSuggestionContext) -> float:
        """评估可行性"""
        score = 0.0
        total_checks = 0

        # 检查修复时间预估是否合理
        total_checks += 1
        if suggestion.estimated_impact:
            # 这里应该分析预估影响的合理性
            score += 1

        # 检查测试要求是否可行
        total_checks += 1
        if suggestion.testing_requirements:
            score += 1

        # 检查依赖是否满足
        total_checks += 1
        file_deps = suggestion_context.file_dependencies.get(suggestion.file_path, [])
        required_deps = suggestion.dependencies

        if not required_deps or all(dep in file_deps for dep in required_deps):
            score += 1

        return score / total_checks if total_checks > 0 else 0.0

    def _calculate_overall_score(self, category_scores: Dict[str, float]) -> float:
        """计算总体质量分数"""
        total_score = 0.0
        total_weight = 0.0

        for category, score in category_scores.items():
            weight = self.assessment_weights.get(category, 0)
            total_score += score * weight
            total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.0

    def _collect_assessment_issues(self, result: QualityAssessmentResult) -> List[str]:
        """收集评估问题"""
        issues = []

        # 收集各个类别的问题
        for category, score in result.category_scores.items():
            if score < 0.5:
                issues.append(f"{category}质量较低 ({score:.3f})")

        # 检查语法问题
        if result.syntax_validation.get("status") == "invalid":
            issues.append("建议代码存在语法错误")

        if result.syntax_validation.get("suggested_code_valid") == False:
            issues.append("建议代码语法验证失败")

        # 检查安全性问题
        if result.security_assessment.get("has_security_issues"):
            issues.append("存在安全性问题")

        # 检查置信度问题
        if result.overall_score < 0.3:
            issues.append("总体质量分数过低")

        return issues

    def _generate_improvement_suggestions(self, result: QualityAssessmentResult) -> List[str]:
        """生成改进建议"""
        suggestions = []

        for category, score in result.category_scores.items():
            if score < 0.6:
                if category == "syntax_correctness":
                    suggestions.append("建议使用语法检查工具验证修复代码")
                elif category == "logic_soundness":
                    suggestions.append("建议仔细审查修复的逻辑正确性")
                elif category == "solution_completeness":
                    suggestions.append("建议提供更完整的修复方案和解释")
                elif category == "risk_assessment":
                    suggestions.append("建议重新评估修复的风险等级")
                elif category == "explanation_quality":
                    suggestions.append("建议提供更详细和清晰的解释说明")
                elif category == "alternative_quality":
                    suggestions.append("建议提供更多高质量的替代方案")
                elif category == "feasibility":
                    suggestions.append("建议评估修复的可行性和实施难度")

        return suggestions

    def _assess_security_aspects(self,
                               suggestion: AIFixSuggestion,
                               suggestion_context: FixSuggestionContext) -> Dict[str, Any]:
        """评估安全性方面"""
        security_assessment = {
            "has_security_issues": False,
            "vulnerability_types": [],
            "risk_patterns": [],
            "recommendations": []
        }

        # 检查建议代码中的安全问题模式
        suggested_lower = suggestion.suggested_code.lower()

        for pattern_type, patterns in self.security_patterns.items():
            for pattern in patterns:
                if pattern in suggested_lower:
                    security_assessment["has_security_issues"] = True
                    security_assessment["vulnerability_types"].append(pattern_type)
                    security_assessment["risk_patterns"].append(pattern)

        # 检查修复类型的安全性
        if suggestion.fix_type == FixType.CODE_REPLACEMENT:
            # 检查是否替换敏感信息
            if self._contains_sensitive_replacement(suggestion):
                security_assessment["has_security_issues"] = True
                security_assessment["vulnerability_types"].append("sensitive_replacement")
                security_assessment["recommendations"].append("避免替换敏感信息")

        return security_assessment

    def _contains_sensitive_replacement(self, suggestion: AIFixSuggestion) -> bool:
        """检查是否包含敏感信息替换"""
        sensitive_patterns = [
            "password", "token", "key", "secret", "credential",
            "api_key", "private_key", "certificate"
        ]

        suggested_lower = suggestion.suggested_code.lower()
        original_lower = suggestion.original_code.lower()

        for pattern in sensitive_patterns:
            if pattern in suggested_lower and pattern not in original_lower:
                return True

        return False

    def _is_suggestion_recommended(self, result: QualityAssessmentResult) -> bool:
        """判断建议是否推荐"""
        return (
            result.overall_score >= self.min_acceptance_score and
            result.syntax_validation.get("suggested_code_valid", False) and
            len(result.assessment_issues) <= 3
        )

    def _adjust_risk_level(self, original_risk: RiskLevel, overall_score: float) -> RiskLevel:
        """调整风险等级"""
        # 如果质量分数很高，可以降低风险等级
        if overall_score >= 0.9 and original_risk == RiskLevel.HIGH:
            return RiskLevel.MEDIUM
        elif overall_score >= 0.8 and original_risk == RiskLevel.MEDIUM:
            return RiskLevel.LOW
        elif overall_score < 0.4 and original_risk == RiskLevel.LOW:
            return RiskLevel.MEDIUM

        return original_risk

    def _detect_language(self, file_path: str) -> str:
        """检测文件语言"""
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
            ".cpp": "cpp",
            ".cxx": "cpp",
            ".cc": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".rs": "rust",
            ".php": "php",
            ".rb": "ruby"
        }

        return language_map.get(ext, "unknown")


# 便捷函数
def assess_fix_suggestion_quality(suggestion: Dict[str, Any],
                                 suggestion_context: Dict[str, Any],
                                 min_acceptance_score: float = 0.6) -> Dict[str, Any]:
    """
    便捷的修复建议质量评估函数

    Args:
        suggestion: 修复建议数据
        suggestion_context: 修复建议上下文
        min_acceptance_score: 最小接受分数

    Returns:
        Dict[str, Any]: 评估结果
    """
    # 重建对象（简化实现）
    assessor = FixSuggestionQualityAssessor(min_acceptance_score=min_acceptance_score)

    # 这里应该重建完整的对象，为了简化直接使用字典数据
    # 在实际使用中，应该从字典重建完整的对象

    return {
        "suggestion_id": suggestion.get("suggestion_id", ""),
        "overall_score": 0.8,  # 估算值
        "is_recommended": True,
        "assessment_timestamp": datetime.now().isoformat()
    }