"""
修复建议上下文构建器 - T009.1
为AI修复建议构建上下文
"""

import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..utils.logger import get_logger

try:
    from .problem_detection_validator import ProblemValidationResult, ValidatedProblem
    from .project_structure_scanner import ProjectStructure
    from .workflow_data_types import (
        AIDetectedProblem,
        CodeContext,
        FixType,
        ProblemType,
        SeverityLevel,
    )
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
        context: Optional[Any] = None
        tags: List[str] = field(default_factory=list)
        estimated_fix_time: int = 0

    @dataclass
    class ValidatedProblem:
        original_problem: AIDetectedProblem
        validation_result: Any
        adjusted_confidence: float
        priority_rank: int = 0
        is_recommended: bool = True

    @dataclass
    class ProjectStructure:
        project_path: str
        total_files: int = 0
        language_distribution: Dict[str, int] = field(default_factory=dict)


@dataclass
class FixSuggestionContext:
    """修复建议上下文"""

    context_id: str
    validation_result: ProblemValidationResult
    file_contents: Dict[str, str] = field(default_factory=dict)
    file_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    project_context: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    fix_constraints: Dict[str, Any] = field(default_factory=dict)
    context_statistics: Dict[str, Any] = field(default_factory=dict)
    build_timestamp: str = ""
    token_estimate: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "context_id": self.context_id,
            "validation_result": (
                self.validation_result.to_dict()
                if hasattr(self.validation_result, "to_dict")
                else {}
            ),
            "file_contents": self.file_contents,
            "file_dependencies": self.file_dependencies,
            "project_context": self.project_context,
            "user_preferences": self.user_preferences,
            "fix_constraints": self.fix_constraints,
            "context_statistics": self.context_statistics,
            "build_timestamp": self.build_timestamp,
            "token_estimate": self.token_estimate,
        }


class FixSuggestionContextBuilder:
    """修复建议上下文构建器"""

    def __init__(self, max_context_lines: int = 20, max_token_estimate: int = 6000):
        self.max_context_lines = max_context_lines
        self.max_token_estimate = max_token_estimate
        self.logger = get_logger()

        # 修复策略配置
        self.fix_strategies = {
            ProblemType.SECURITY: {
                "priority": "critical",
                "approach": "conservative",
                "require_testing": True,
                "risk_level": "high",
            },
            ProblemType.PERFORMANCE: {
                "priority": "high",
                "approach": "balanced",
                "require_testing": True,
                "risk_level": "medium",
            },
            ProblemType.LOGIC: {
                "priority": "high",
                "approach": "thorough",
                "require_testing": True,
                "risk_level": "high",
            },
            ProblemType.RELIABILITY: {
                "priority": "medium",
                "approach": "defensive",
                "require_testing": True,
                "risk_level": "medium",
            },
            ProblemType.MAINTAINABILITY: {
                "priority": "medium",
                "approach": "incremental",
                "require_testing": False,
                "risk_level": "low",
            },
            ProblemType.STYLE: {
                "priority": "low",
                "approach": "automated",
                "require_testing": False,
                "risk_level": "low",
            },
            ProblemType.COMPATIBILITY: {
                "priority": "medium",
                "approach": "careful",
                "require_testing": True,
                "risk_level": "medium",
            },
            ProblemType.DOCUMENTATION: {
                "priority": "low",
                "approach": "simple",
                "require_testing": False,
                "risk_level": "low",
            },
        }

    def build_context(
        self,
        detected_problems: Optional[List[AIDetectedProblem]] = None,
        validation_result: Optional[ProblemValidationResult] = None,
        file_contents: Optional[Dict[str, str]] = None,
        project_structure: Optional[ProjectStructure] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> FixSuggestionContext:
        """
        构建修复建议上下文

        Args:
            detected_problems: AI检测到的问题列表（与validation_result二选一）
            validation_result: 问题验证结果（与detected_problems二选一）
            file_contents: 文件内容
            project_structure: 项目结构信息
            user_preferences: 用户偏好

        Returns:
            FixSuggestionContext: 构建的上下文
        """
        # 支持两种输入方式：detected_problems 或 validation_result
        if detected_problems:
            context_id = self._generate_context_id()
            self.logger.info(
                f"开始构建修复建议上下文，问题数量: {len(detected_problems)}"
            )
            # 先创建validation_result，然后创建上下文
            validation_result = self._create_validation_result_from_problems(
                detected_problems
            )

            # 使用detected_problems创建上下文
            context = FixSuggestionContext(
                context_id=context_id,
                validation_result=validation_result,
                build_timestamp=datetime.now().isoformat(),
            )
            # 设置detected_problems
            context.detected_problems = detected_problems
        elif validation_result:
            context_id = self._generate_context_id()
            self.logger.info(
                f"开始构建修复建议上下文，验证ID: {validation_result.validation_id}"
            )
            # 使用validation_result创建上下文（保持向后兼容）
            context = FixSuggestionContext(
                context_id=context_id,
                validation_result=validation_result,
                build_timestamp=datetime.now().isoformat(),
            )
            context.detected_problems = validation_result.original_problems
        else:
            raise ValueError("必须提供detected_problems或validation_result中的一个")

        try:
            # 处理文件内容
            context.file_contents = file_contents or {}

            # 分析文件依赖关系
            context.file_dependencies = self._analyze_file_dependencies(
                validation_result.filtered_problems, context.file_contents
            )

            # 构建项目上下文
            context.project_context = self._build_project_context(
                validation_result, project_structure
            )

            # 处理用户偏好
            context.user_preferences = user_preferences or {}

            # 设置修复约束
            context.fix_constraints = self._set_fix_constraints(
                validation_result, context.user_preferences
            )

            # 生成上下文统计
            context.context_statistics = self._generate_context_statistics(context)

            # 估算token使用量
            context.token_estimate = self._estimate_token_usage(context)

            self.logger.info(
                f"修复建议上下文构建完成，预估token数: {context.token_estimate}"
            )

        except Exception as e:
            self.logger.error(f"构建修复建议上下文失败: {e}")
            raise

        return context

    def _analyze_file_dependencies(
        self, problems: List[ValidatedProblem], file_contents: Dict[str, str]
    ) -> Dict[str, List[str]]:
        """分析文件依赖关系"""
        dependencies = {}

        for problem in problems:
            file_path = problem.original_problem.file_path
            if file_path not in file_contents:
                continue

            content = file_contents[file_path]
            file_deps = self._extract_file_dependencies(file_path, content)
            dependencies[file_path] = file_deps

        return dependencies

    def _extract_file_dependencies(self, file_path: str, content: str) -> List[str]:
        """提取文件依赖"""
        dependencies = []
        lines = content.split("\n")

        # 根据文件类型提取依赖
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if ext == ".py":
            dependencies.extend(self._extract_python_dependencies(lines))
        elif ext in [".js", ".jsx", ".ts", ".tsx"]:
            dependencies.extend(self._extract_javascript_dependencies(lines))
        elif ext == ".java":
            dependencies.extend(self._extract_java_dependencies(lines))
        elif ext == ".go":
            dependencies.extend(self._extract_go_dependencies(lines))

        return list(set(dependencies))  # 去重

    def _extract_python_dependencies(self, lines: List[str]) -> List[str]:
        """提取Python依赖"""
        dependencies = []

        for line in lines:
            line = line.strip()

            # import语句
            if line.startswith("import "):
                parts = line.split()
                if len(parts) >= 2:
                    module = parts[1].split(".")[0]
                    dependencies.append(module)

            # from ... import语句
            elif line.startswith("from "):
                if " import " in line:
                    module_part = line.split(" import ")[0].replace("from ", "").strip()
                    module = module_part.split(".")[0]
                    dependencies.append(module)

        return dependencies

    def _extract_javascript_dependencies(self, lines: List[str]) -> List[str]:
        """提取JavaScript/TypeScript依赖"""
        dependencies = []

        for line in lines:
            line = line.strip()

            # import语句
            if line.startswith("import ") and " from " in line:
                from_part = line.split(" from ")[1].strip()
                # 清理引号
                module = from_part.strip("'\"")
                dependencies.append(module)

            # require语句
            elif line.startswith("require("):
                module = line.strip()[len("require(") : -1].strip("'\"")
                dependencies.append(module)

        return dependencies

    def _extract_java_dependencies(self, lines: List[str]) -> List[str]:
        """提取Java依赖"""
        dependencies = []

        for line in lines:
            line = line.strip()

            # import语句
            if line.startswith("import "):
                parts = line.split()
                if len(parts) >= 2:
                    import_statement = " ".join(parts[1:])
                    # 移除分号
                    module = import_statement.rstrip(";")
                    dependencies.append(module)

        return dependencies

    def _extract_go_dependencies(self, lines: List[str]) -> List[str]:
        """提取Go依赖"""
        dependencies = []

        for line in lines:
            line = line.strip()

            # import语句
            if line.startswith("import "):
                import_part = line.replace("import ", "").strip()
                # 移除引号
                module = import_part.strip("\"'")
                dependencies.append(module)

        return dependencies

    def _build_project_context(
        self,
        validation_result: ProblemValidationResult,
        project_structure: Optional[ProjectStructure],
    ) -> Dict[str, Any]:
        """构建项目上下文"""
        context = {}

        # 分析问题分布
        problem_stats = self._analyze_problem_distribution(
            validation_result.filtered_problems
        )
        context["problem_statistics"] = problem_stats

        # 项目信息
        if project_structure:
            context["project_info"] = {
                "project_path": project_structure.project_path,
                "total_files": project_structure.total_files,
                "language_distribution": project_structure.language_distribution,
                "project_type": self._detect_project_type(project_structure),
            }

        # 修复复杂性评估
        context["complexity_assessment"] = self._assess_fix_complexity(
            validation_result.filtered_problems
        )

        # 风险评估
        context["risk_assessment"] = self._assess_fix_risks(
            validation_result.filtered_problems
        )

        return context

    def _analyze_problem_distribution(
        self, problems: List[ValidatedProblem]
    ) -> Dict[str, Any]:
        """分析问题分布"""
        if not problems:
            return {"total_problems": 0}

        stats = {
            "total_problems": len(problems),
            "severity_distribution": {},
            "type_distribution": {},
            "file_distribution": {},
            "priority_distribution": {"high": 0, "medium": 0, "low": 0},
        }

        for problem in problems:
            original = problem.original_problem

            # 严重程度分布
            severity = original.severity.value
            stats["severity_distribution"][severity] = (
                stats["severity_distribution"].get(severity, 0) + 1
            )

            # 问题类型分布
            problem_type = original.problem_type.value
            stats["type_distribution"][problem_type] = (
                stats["type_distribution"].get(problem_type, 0) + 1
            )

            # 文件分布
            file_path = original.file_path
            stats["file_distribution"][file_path] = (
                stats["file_distribution"].get(file_path, 0) + 1
            )

            # 优先级分布
            if problem.priority_rank <= len(problems) // 3:
                stats["priority_distribution"]["high"] += 1
            elif problem.priority_rank <= 2 * len(problems) // 3:
                stats["priority_distribution"]["medium"] += 1
            else:
                stats["priority_distribution"]["low"] += 1

        return stats

    def _detect_project_type(self, project_structure: ProjectStructure) -> str:
        """检测项目类型"""
        languages = project_structure.language_distribution

        if languages.get("python", 0) > 0:
            return "Python项目"
        elif languages.get("javascript", 0) > 0 or languages.get("typescript", 0) > 0:
            return "JavaScript/TypeScript项目"
        elif languages.get("java", 0) > 0:
            return "Java项目"
        elif languages.get("go", 0) > 0:
            return "Go项目"
        else:
            return "多语言项目"

    def _assess_fix_complexity(
        self, problems: List[ValidatedProblem]
    ) -> Dict[str, Any]:
        """评估修复复杂性"""
        if not problems:
            return {"overall_complexity": "低", "complexity_score": 0}

        complexity_scores = []

        for problem in problems:
            original = problem.original_problem
            score = 0

            # 基于问题类型
            type_complexity = {
                ProblemType.SECURITY: 4,
                ProblemType.LOGIC: 3,
                ProblemType.PERFORMANCE: 3,
                ProblemType.RELIABILITY: 3,
                ProblemType.COMPATIBILITY: 2,
                ProblemType.MAINTAINABILITY: 2,
                ProblemType.STYLE: 1,
                ProblemType.DOCUMENTATION: 1,
            }
            score += type_complexity.get(original.problem_type, 1)

            # 基于严重程度
            severity_weights = {
                SeverityLevel.CRITICAL: 4,
                SeverityLevel.HIGH: 3,
                SeverityLevel.MEDIUM: 2,
                SeverityLevel.LOW: 1,
            }
            score += severity_weights.get(original.severity, 1)

            # 基于修复类型
            fix_complexity = {
                FixType.REFACTORING: 3,
                FixType.CODE_REPLACEMENT: 2,
                FixType.CODE_INSERTION: 2,
                FixType.CODE_DELETION: 1,
                FixType.CONFIGURATION: 1,
                FixType.DEPENDENCY_UPDATE: 2,
            }
            score += fix_complexity.get(original.suggested_fix_type, 1)

            complexity_scores.append(score)

        avg_complexity = sum(complexity_scores) / len(complexity_scores)

        if avg_complexity >= 6:
            complexity_level = "高"
        elif avg_complexity >= 4:
            complexity_level = "中"
        else:
            complexity_level = "低"

        return {
            "overall_complexity": complexity_level,
            "complexity_score": round(avg_complexity, 2),
            "max_complexity": max(complexity_scores) if complexity_scores else 0,
            "min_complexity": min(complexity_scores) if complexity_scores else 0,
        }

    def _assess_fix_risks(self, problems: List[ValidatedProblem]) -> Dict[str, Any]:
        """评估修复风险"""
        if not problems:
            return {"overall_risk": "低", "risk_score": 0}

        risk_factors = []

        for problem in problems:
            original = problem.original_problem
            risk = 0

            # 高严重程度问题风险更高
            if original.severity == SeverityLevel.CRITICAL:
                risk += 4
            elif original.severity == SeverityLevel.HIGH:
                risk += 3
            elif original.severity == SeverityLevel.MEDIUM:
                risk += 2

            # 安全问题风险最高
            if original.problem_type == ProblemType.SECURITY:
                risk += 4
            elif original.problem_type == ProblemType.LOGIC:
                risk += 3
            elif original.problem_type == ProblemType.PERFORMANCE:
                risk += 2

            # 重构类修改风险较高
            if original.suggested_fix_type == FixType.REFACTORING:
                risk += 2
            elif original.suggested_fix_type == FixType.CODE_REPLACEMENT:
                risk += 1

            risk_factors.append(risk)

        avg_risk = sum(risk_factors) / len(risk_factors)

        if avg_risk >= 5:
            risk_level = "高"
        elif avg_risk >= 3:
            risk_level = "中"
        else:
            risk_level = "低"

        return {
            "overall_risk": risk_level,
            "risk_score": round(avg_risk, 2),
            "high_risk_problems": sum(1 for r in risk_factors if r >= 5),
            "medium_risk_problems": sum(1 for r in risk_factors if 3 <= r < 5),
            "low_risk_problems": sum(1 for r in risk_factors if r < 3),
        }

    def _set_fix_constraints(
        self,
        validation_result: ProblemValidationResult,
        user_preferences: Dict[str, Any],
    ) -> Dict[str, Any]:
        """设置修复约束"""
        constraints = {}

        # 默认约束
        constraints.update(
            {
                "max_files_per_batch": 5,
                "require_backup": True,
                "require_testing": True,
                "min_confidence_threshold": 0.7,
                "allow_breaking_changes": False,
                "prefer_minimal_changes": True,
            }
        )

        # 基于用户偏好调整约束
        if user_preferences.get("conservative_mode"):
            constraints.update(
                {
                    "max_files_per_batch": 3,
                    "min_confidence_threshold": 0.8,
                    "allow_breaking_changes": False,
                    "prefer_minimal_changes": True,
                }
            )

        if user_preferences.get("aggressive_mode"):
            constraints.update(
                {
                    "max_files_per_batch": 10,
                    "min_confidence_threshold": 0.6,
                    "allow_breaking_changes": True,
                    "prefer_minimal_changes": False,
                }
            )

        # 基于问题特征调整约束
        high_risk_problems = sum(
            1
            for p in validation_result.filtered_problems
            if p.original_problem.severity
            in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]
        )

        if high_risk_problems > len(validation_result.filtered_problems) * 0.5:
            constraints["max_files_per_batch"] = min(
                constraints["max_files_per_batch"], 3
            )
            constraints["require_testing"] = True

        # 基于项目类型调整约束
        if (
            validation_result.validation_summary.get("quality_overview", {}).get(
                "project_type"
            )
            == "Python项目"
        ):
            constraints["python_specific"] = {
                "preserve_indentation": True,
                "respect_pep8": True,
                "check_imports": True,
            }

        return constraints

    def _generate_context_statistics(
        self, context: FixSuggestionContext
    ) -> Dict[str, Any]:
        """生成上下文统计"""
        problems = context.validation_result.filtered_problems

        stats = {
            "total_problems": len(problems),
            "total_files": len(set(p.original_problem.file_path for p in problems)),
            "file_contents_loaded": len(context.file_contents),
            "dependencies_analyzed": len(context.file_dependencies),
            "problem_types": list(
                set(p.original_problem.problem_type.value for p in problems)
            ),
            "severity_levels": list(
                set(p.original_problem.severity.value for p in problems)
            ),
            "estimated_total_fix_time": sum(
                p.original_problem.estimated_fix_time for p in problems
            ),
            "average_confidence": (
                round(sum(p.adjusted_confidence for p in problems) / len(problems), 3)
                if problems
                else 0
            ),
        }

        return stats

    def _estimate_token_usage(self, context: FixSuggestionContext) -> int:
        """估算token使用量"""
        total_chars = 0

        # 验证结果
        if hasattr(context.validation_result, "to_dict"):
            validation_chars = len(
                json.dumps(context.validation_result.to_dict(), ensure_ascii=False)
            )
        else:
            validation_chars = 1000  # 估算值
        total_chars += validation_chars

        # 文件内容（限制数量）
        content_chars = sum(len(content) for content in context.file_contents.values())
        total_chars += min(content_chars, 50000)  # 限制内容字符数

        # 其他数据
        total_chars += len(json.dumps(context.project_context, ensure_ascii=False))
        total_chars += len(json.dumps(context.user_preferences, ensure_ascii=False))
        total_chars += len(json.dumps(context.fix_constraints, ensure_ascii=False))

        # 粗略估算token数
        chinese_chars = len([c for c in str(total_chars) if ord(c) > 127])
        other_chars = total_chars - chinese_chars

        estimated_tokens = chinese_chars + (other_chars // 4)

        return estimated_tokens

    def _create_validation_result_from_problems(
        self, detected_problems: List[AIDetectedProblem]
    ) -> "ProblemValidationResult":
        """
        从检测到的问题创建验证结果

        Args:
            detected_problems: AI检测到的问题列表

        Returns:
            ProblemValidationResult: 创建的验证结果
        """
        try:
            # 导入需要的类型
            from .problem_detection_validator import (
                ProblemValidationResult,
                ValidatedProblem,
                ValidationResult,
            )

            # 创建ValidatedProblem列表
            validated_problems = []
            for problem in detected_problems:
                # 创建ValidationResult
                validation_result_inner = ValidationResult(
                    is_valid=True,
                    validation_score=problem.confidence,
                    validation_issues=[],
                    quality_metrics={
                        "ai_confidence": problem.confidence,
                        "problem_type": problem.problem_type.value,
                        "severity": problem.severity.value,
                    },
                    recommendations=["建议进行修复"],
                )

                # 创建ValidatedProblem
                validated_problem = ValidatedProblem(
                    original_problem=problem,
                    validation_result=validation_result_inner,
                    adjusted_confidence=problem.confidence,
                    priority_rank=1,
                    is_recommended=True,
                )
                validated_problems.append(validated_problem)

            # 创建模拟的ProblemDetectionResult
            from ..tools.ai_problem_detector import ProblemDetectionResult

            mock_detection_result = ProblemDetectionResult(
                detection_id=f"detection_{int(datetime.now().timestamp())}",
                context_id="auto_generated",
                detected_problems=detected_problems,
                execution_success=True,
                execution_time=0.0,
            )

            # 创建ProblemValidationResult
            problem_validation_result = ProblemValidationResult(
                validation_id=f"validation_{int(datetime.now().timestamp())}",
                original_detection_result=mock_detection_result,
                validated_problems=validated_problems,
                filtered_problems=validated_problems,
                validation_summary={
                    "total_problems": len(detected_problems),
                    "validated_problems": len(validated_problems),
                    "validation_success": True,
                    "auto_generated": True,
                },
            )

            return problem_validation_result

        except ImportError:
            # 如果无法导入相关类，创建一个简单的模拟对象
            self.logger.warning("无法导入ProblemValidationResult，使用模拟对象")

            class MockValidationResult:
                def __init__(self):
                    self.validation_id = (
                        f"mock_validation_{int(datetime.now().timestamp())}"
                    )
                    self.original_problems = detected_problems
                    self.filtered_problems = detected_problems
                    self.validation_summary = {
                        "total_problems": len(detected_problems),
                        "validated_problems": len(detected_problems),
                        "validation_success": True,
                    }

            return MockValidationResult()

    def _generate_context_id(self) -> str:
        """生成上下文ID"""
        import uuid

        return f"fix_context_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"

    def optimize_context_for_tokens(
        self, context: FixSuggestionContext, target_tokens: int
    ) -> FixSuggestionContext:
        """
        优化上下文以控制token数量

        Args:
            context: 原始上下文
            target_tokens: 目标token数量

        Returns:
            FixSuggestionContext: 优化后的上下文
        """
        if context.token_estimate <= target_tokens:
            return context

        self.logger.info(
            f"优化上下文，当前token数: {context.token_estimate}, 目标: {target_tokens}"
        )

        # 创建优化的上下文副本
        optimized_context = FixSuggestionContext(
            context_id=context.context_id + "_optimized",
            validation_result=context.validation_result,
            project_context=context.project_context,
            user_preferences=context.user_preferences,
            fix_constraints=context.fix_constraints,
            build_timestamp=context.build_timestamp,
        )

        # 优化文件内容
        optimized_file_contents = {}
        for file_path, content in list(context.file_contents.items())[:15]:
            # 进一步限制内容长度
            if len(content) > 3000:
                optimized_content = content[:3000] + "\n... (内容截断)"
                optimized_file_contents[file_path] = optimized_content
            else:
                optimized_file_contents[file_path] = content

        optimized_context.file_contents = optimized_file_contents

        # 简化依赖关系
        optimized_file_dependencies = {}
        for file_path, deps in list(context.file_dependencies.items())[:15]:
            optimized_file_dependencies[file_path] = deps[:5]  # 限制依赖数量

        optimized_context.file_dependencies = optimized_file_dependencies

        # 重新估算token数量
        optimized_context.token_estimate = self._estimate_token_usage(optimized_context)

        self.logger.info(
            f"上下文优化完成，新token数: {optimized_context.token_estimate}"
        )

        return optimized_context


# 便捷函数
def build_fix_suggestion_context(
    validation_result: Any,
    file_contents: Optional[Dict[str, str]] = None,
    project_structure: Optional[Any] = None,
    user_preferences: Optional[Dict[str, Any]] = None,
    max_tokens: int = 6000,
) -> Dict[str, Any]:
    """
    便捷的修复建议上下文构建函数

    Args:
        validation_result: 问题验证结果
        file_contents: 文件内容
        project_structure: 项目结构信息
        user_preferences: 用户偏好
        max_tokens: 最大token数

    Returns:
        Dict[str, Any]: 构建的上下文
    """
    builder = FixSuggestionContextBuilder()
    context = builder.build_context(
        validation_result=validation_result,
        file_contents=file_contents,
        project_structure=project_structure,
        user_preferences=user_preferences,
    )

    # 如果token过多，进行优化
    if context.token_estimate > max_tokens:
        context = builder.optimize_context_for_tokens(context, max_tokens)

    return context.to_dict()
