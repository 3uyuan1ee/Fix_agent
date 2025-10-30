"""
AI修复建议生成器 - T009.2
生成AI修复建议
"""

import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..utils.logger import get_logger
try:
    from .fix_suggestion_context_builder import FixSuggestionContext
    from .problem_detection_validator import ValidatedProblem
    from .workflow_data_types import AIFixSuggestion, AlternativeFix, ProblemType, SeverityLevel, FixType, RiskLevel
    from ..llm.unified_llm_client import UnifiedLLMClient
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

    class RiskLevel(Enum):
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"

    @dataclass
    class AlternativeFix:
        fix_id: str
        approach: str
        code: str
        pros: List[str] = field(default_factory=list)
        cons: List[str] = field(default_factory=list)
        risk_level: RiskLevel = RiskLevel.MEDIUM
        estimated_time: int = 0
        compatibility: Dict[str, bool] = field(default_factory=dict)

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
        alternatives: List[AlternativeFix] = field(default_factory=list)
        estimated_impact: str = ""
        fix_type: FixType = FixType.CODE_REPLACEMENT
        dependencies: List[str] = field(default_factory=list)
        testing_requirements: List[str] = field(default_factory=list)
        generation_timestamp: datetime = field(default_factory=datetime.now)

    @dataclass
    class ValidatedProblem:
        original_problem: Any
        validation_result: Any
        adjusted_confidence: float
        priority_rank: int = 0
        is_recommended: bool = True

    @dataclass
    class FixSuggestionContext:
        context_id: str
        validation_result: Any
        file_contents: Dict[str, str] = field(default_factory=dict)
        file_dependencies: Dict[str, List[str]] = field(default_factory=dict)
        project_context: Dict[str, Any] = field(default_factory=dict)
        user_preferences: Dict[str, Any] = field(default_factory=dict)
        fix_constraints: Dict[str, Any] = field(default_factory=dict)

    class UnifiedLLMClient:
        def __init__(self, *args, **kwargs):
            pass

        def chat_completion(self, *args, **kwargs):
            return {"content": '{"fix_suggestions": []}', "success": True}


@dataclass
class FixSuggestionResult:
    """修复建议结果"""
    suggestion_id: str
    context_id: str
    fix_suggestions: List[AIFixSuggestion] = field(default_factory=list)
    suggestion_summary: Dict[str, Any] = field(default_factory=dict)
    execution_success: bool = True
    execution_time: float = 0.0
    error_message: str = ""
    ai_responses: List[Dict[str, Any]] = field(default_factory=list)
    token_usage: Dict[str, int] = field(default_factory=dict)
    generation_timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "suggestion_id": self.suggestion_id,
            "context_id": self.context_id,
            "fix_suggestions": [suggestion.to_dict() for suggestion in self.fix_suggestions],
            "suggestion_summary": self.suggestion_summary,
            "execution_success": self.execution_success,
            "execution_time": self.execution_time,
            "error_message": self.error_message,
            "ai_responses": self.ai_responses,
            "token_usage": self.token_usage,
            "generation_timestamp": self.generation_timestamp,
            "total_suggestions": len(self.fix_suggestions)
        }


class AIFixSuggestionGenerator:
    """AI修复建议生成器"""

    def __init__(self,
                 llm_client: Optional[Any] = None,
                 max_concurrent_suggestions: int = 3,
                 max_retries: int = 3,
                 retry_delay: float = 1.0):
        self.llm_client = llm_client
        self.max_concurrent_suggestions = max_concurrent_suggestions
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = get_logger()

        # 生成配置
        self.generation_config = {
            "temperature": 0.4,  # 稍高温度以获得创意性解决方案
            "max_tokens": 2500,  # 每次AI调用的最大token数
            "timeout": 90,  # 单次AI调用超时时间（秒）
            "min_confidence": 0.6,  # 最小置信度阈值
            "max_alternatives": 3,  # 最大替代方案数量
            "include_risk_assessment": True,
            "include_testing_requirements": True
        }

        # 系统提示词模板
        self.system_prompt_template = """
你是一个资深的代码修复专家，擅长为各种编程问题提供高质量的修复方案。

你的任务是为检测到的问题生成具体的、可执行的修复建议。

修复要求：
1. **代码质量**: 确保修复代码符合最佳实践和编码规范
2. **功能正确性**: 修复必须解决根本问题，不能引入新问题
3. **向后兼容**: 避免破坏性变更，除非问题本身需要
4. **可维护性**: 修复后的代码应该易于理解和维护
5. **性能考虑**: 修复不应显著影响性能

输出格式：
严格按照JSON格式输出，包含fix_suggestions数组，每个建议包含：
- suggestion_id: 建议唯一标识
- problem_id: 问题ID
- file_path: 文件路径
- line_number: 行号
- original_code: 原始代码
- suggested_code: 建议修复代码
- explanation: 修复说明
- reasoning: 修复推理过程
- confidence: 置信度 (0.0-1.0)
- risk_level: 风险级别 (low/medium/high)
- side_effects: 潜在副作用列表
- alternatives: 替代方案数组（可选）
- estimated_impact: 修复影响评估
- fix_type: 修复类型
- testing_requirements: 测试要求

特殊说明：
- 如果问题有多种解决方案，请提供替代方案
- 始终提供详细的修复理由和潜在影响分析
- 评估修复的风险等级和测试要求
- 确保修复代码语法正确且符合语言规范
"""

    def generate_suggestions(self,
                            suggestion_context: FixSuggestionContext,
                            focus_problems: Optional[List[str]] = None) -> FixSuggestionResult:
        """
        生成修复建议

        Args:
            suggestion_context: 修复建议上下文
            focus_problems: 重点处理的问题ID列表（可选）

        Returns:
            FixSuggestionResult: 生成结果
        """
        start_time = time.time()
        self.logger.info(f"开始生成修复建议，上下文ID: {suggestion_context.context_id}")

        result = FixSuggestionResult(
            suggestion_id=self._generate_suggestion_id(),
            context_id=suggestion_context.context_id,
            generation_timestamp=datetime.now().isoformat()
        )

        try:
            # 筛选要处理的问题
            problems_to_process = self._select_problems_for_suggestion(
                suggestion_context.validation_result.filtered_problems, focus_problems
            )

            self.logger.info(f"选择 {len(problems_to_process)} 个问题生成修复建议")

            # 并行生成修复建议
            suggestions = self._generate_suggestions_parallel(
                problems_to_process, suggestion_context
            )

            # 验证和优化建议
            result.fix_suggestions = self._validate_and_optimize_suggestions(
                suggestions, suggestion_context
            )

            # 生成建议摘要
            result.suggestion_summary = self._generate_suggestion_summary(
                result.fix_suggestions, suggestion_context
            )

            # 计算执行时间
            result.execution_time = time.time() - start_time

            self.logger.info(
                f"修复建议生成完成: 生成 {len(result.fix_suggestions)} 个建议, "
                f"耗时 {result.execution_time:.2f}秒"
            )

        except Exception as e:
            result.execution_success = False
            result.error_message = f"修复建议生成失败: {e}"
            result.execution_time = time.time() - start_time
            self.logger.error(result.error_message)

        return result

    def _select_problems_for_suggestion(self,
                                       validated_problems: List[ValidatedProblem],
                                       focus_problems: Optional[List[str]]) -> List[ValidatedProblem]:
        """选择要生成建议的问题"""
        if focus_problems:
            # 如果指定了重点问题，只处理这些问题
            focused_problems = []
            for problem in validated_problems:
                if problem.original_problem.problem_id in focus_problems:
                    focused_problems.append(problem)
            return focused_problems

        # 否则按优先级选择，最多处理15个问题
        sorted_problems = sorted(
            validated_problems,
            key=lambda x: x.priority_rank
        )

        return sorted_problems[:15]

    def _generate_suggestions_parallel(self,
                                      problems_to_process: List[ValidatedProblem],
                                      suggestion_context: FixSuggestionContext) -> List[AIFixSuggestion]:
        """并行生成修复建议"""
        all_suggestions = []

        with ThreadPoolExecutor(max_workers=self.max_concurrent_suggestions) as executor:
            # 提交生成任务
            future_to_problem = {}
            for problem in problems_to_process:
                future = executor.submit(
                    self._generate_single_suggestion,
                    problem,
                    suggestion_context
                )
                future_to_problem[future] = problem

            # 收集结果
            for future in as_completed(future_to_problem):
                problem = future_to_problem[future]
                try:
                    suggestions = future.result(timeout=150)
                    all_suggestions.extend(suggestions)
                    self.logger.info(
                        f"问题 {problem.original_problem.problem_id} "
                        f"建议生成完成，生成 {len(suggestions)} 个建议"
                    )
                except Exception as e:
                    self.logger.error(
                        f"问题 {problem.original_problem.problem_id} "
                        f"建议生成失败: {e}"
                    )

        return all_suggestions

    def _generate_single_suggestion(self,
                                   problem: ValidatedProblem,
                                   suggestion_context: FixSuggestionContext) -> List[AIFixSuggestion]:
        """为单个问题生成修复建议"""
        problem_data = problem.original_problem
        problem_id = problem_data.problem_id

        self.logger.debug(f"开始为问题 {problem_id} 生成修复建议")

        # 构建修复建议提示词
        user_prompt = self._build_suggestion_prompt(problem, suggestion_context)

        # 调用AI生成建议
        ai_response = self._call_ai_with_retry(user_prompt)

        if not ai_response.get("success", False):
            self.logger.warning(f"AI生成建议失败: {ai_response.get('error_message', '未知错误')}")
            return []

        # 解析AI响应
        try:
            response_content = ai_response.get("content", "")
            suggestion_data = json.loads(response_content)

            # 转换为AIFixSuggestion对象
            suggestions = self._parse_ai_suggestions(suggestion_data, problem, suggestion_context)

            return suggestions

        except json.JSONDecodeError as e:
            self.logger.error(f"解析AI响应失败 {problem_id}: {e}")
            return []

    def _build_suggestion_prompt(self,
                               problem: ValidatedProblem,
                               suggestion_context: FixSuggestionContext) -> str:
        """构建修复建议提示词"""
        problem_data = problem.original_problem
        file_path = problem_data.file_path

        # 获取文件内容
        file_content = suggestion_context.file_contents.get(file_path, "")

        # 获取文件依赖
        file_deps = suggestion_context.file_dependencies.get(file_path, [])

        # 构建用户提示词
        prompt_parts = [
            f"# 修复建议生成任务",
            f"",
            f"## 问题信息",
            f"- 问题ID: {problem_data.problem_id}",
            f"- 文件路径: {os.path.basename(file_path)}",
            f"- 行号: {problem_data.line_number}",
            f"- 问题类型: {problem_data.problem_type.value}",
            f"- 严重程度: {problem_data.severity.value}",
            f"- 问题描述: {problem_data.description}",
            f"- 问题推理: {problem_data.reasoning}",
            f"- 置信度: {problem.adjusted_confidence:.2f}",
            f"- 预估修复时间: {problem_data.estimated_fix_time} 分钟",
            f"",
            f"## 问题代码",
            f"```{self._detect_file_language(file_path)}",
            problem_data.code_snippet,
            "```",
            f"",
            f"## 文件上下文"
        ]

        # 添加文件内容
        if file_content:
            lines = file_content.split('\n')
            start_line = max(0, problem_data.line_number - 10)
            end_line = min(len(lines), problem_data.line_number + 10)

            context_lines = lines[start_line:end_line]
            context_content = '\n'.join(context_lines)

            prompt_parts.extend([
                f"```{self._detect_file_language(file_path)}",
                f"# 行 {start_line + 1}-{end_line} (问题在第 {problem_data.line_number} 行)",
                context_content,
                "```"
            ])

        # 添加项目上下文
        if suggestion_context.project_context:
            project_info = suggestion_context.project_context
            prompt_parts.extend([
                f"",
                f"## 项目上下文",
                f"- 项目类型: {project_info.get('project_info', {}).get('project_type', '未知')}",
                f"- 修复复杂性: {project_info.get('complexity_assessment', {}).get('overall_complexity', '中')}",
                f"- 风险评估: {project_info.get('risk_assessment', {}).get('overall_risk', '中')}"
            ])

        # 添加文件依赖
        if file_deps:
            prompt_parts.extend([
                f"",
                f"## 文件依赖",
                f"当前文件依赖: {', '.join(file_deps[:5])}"  # 限制依赖数量
            ])

        # 添加修复约束
        constraints = suggestion_context.fix_constraints
        prompt_parts.extend([
            f"",
            f"## 修复约束",
            f"- 最大修复文件数: {constraints.get('max_files_per_batch', 5)}",
            f"- 要求备份: {'是' if constraints.get('require_backup') else '否'}",
            f"- 要求测试: {'是' if constraints.get('require_testing') else '否'}",
            f"- 最小置信度阈值: {constraints.get('min_confidence_threshold', 0.7)}",
            f"- 允许破坏性变更: {'是' if constraints.get('allow_breaking_changes') else '否'}",
            f"- 偏好最小变更: {'是' if constraints.get('prefer_minimal_changes') else '否'}",
            f"",
            f"## 修复要求",
            f"请为上述问题生成详细的修复建议，包括：",
            f"1. 具体的修复代码（保持语法正确）",
            f"2. 详细的修复说明和理由",
            f"3. 潜在的副作用和风险评估",
            f"4. 如果有多个解决方案，请提供替代方案",
            f"5. 修复的影响评估和测试要求",
            f"",
            f"注意事项：",
            f"- 确保修复代码符合语言规范和最佳实践",
            f"- 考虑修复对其他部分的潜在影响",
            f"- 评估修复的复杂度和风险等级",
            f"- 如果适用，提供测试验证方案",
            f"",
            f"请以JSON格式输出修复建议。"
        ])

        return "\n".join(prompt_parts)

    def _detect_file_language(self, file_path: str) -> str:
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
            ".rb": "ruby",
            ".html": "html",
            ".css": "css",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml"
        }

        return language_map.get(ext, "text")

    def _call_ai_with_retry(self, user_prompt: str) -> Dict[str, Any]:
        """带重试的AI调用"""
        last_error = ""

        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"调用AI模型，尝试 {attempt + 1}/{self.max_retries}")

                if self.llm_client is None:
                    self.llm_client = self._create_default_llm_client()

                # 准备调用参数
                call_params = {
                    "messages": [
                        {"role": "system", "content": self.system_prompt_template},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": self.generation_config["temperature"],
                    "max_tokens": self.generation_config["max_tokens"],
                    "response_format": {"type": "json_object"}
                }

                # 调用AI
                response = self.llm_client.chat_completion(**call_params)

                if response.get("success", False):
                    return response
                else:
                    last_error = response.get("error_message", "未知错误")
                    self.logger.warning(f"AI调用失败: {last_error}")

            except Exception as e:
                last_error = str(e)
                self.logger.error(f"AI调用异常 (尝试 {attempt + 1}): {e}")

            # 如果不是最后一次尝试，等待重试
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (2 ** attempt))

        return {
            "success": False,
            "error_message": f"AI调用失败，已重试 {self.max_retries} 次: {last_error}"
        }

    def _create_default_llm_client(self):
        """创建默认LLM客户端"""
        try:
            from ..llm.unified_llm_client import UnifiedLLMClient
            return UnifiedLLMClient()
        except Exception as e:
            self.logger.error(f"无法创建默认LLM客户端: {e}")
            raise

    def _parse_ai_suggestions(self,
                            suggestion_data: Dict[str, Any],
                            problem: ValidatedProblem,
                            suggestion_context: FixSuggestionContext) -> List[AIFixSuggestion]:
        """解析AI修复建议"""
        suggestions = []
        fix_suggestions = suggestion_data.get("fix_suggestions", [])

        for suggestion_item in fix_suggestions:
            try:
                # 验证必需字段
                if not all(key in suggestion_item for key in [
                    "suggestion_id", "original_code", "suggested_code", "explanation", "reasoning", "confidence"
                ]):
                    continue

                # 解析风险等级
                risk_level = self._parse_risk_level(suggestion_item.get("risk_level", ""))
                if not risk_level:
                    risk_level = RiskLevel.MEDIUM

                # 解析修复类型
                fix_type = self._parse_fix_type(suggestion_item.get("fix_type", ""))

                # 验证置信度
                confidence = float(suggestion_item.get("confidence", 0.0))
                if confidence < self.generation_config["min_confidence"]:
                    continue

                # 解析替代方案
                alternatives = []
                for alt_data in suggestion_item.get("alternatives", []):
                    alternative = AlternativeFix(
                        fix_id=alt_data.get("fix_id", ""),
                        approach=alt_data.get("approach", ""),
                        code=alt_data.get("code", ""),
                        pros=alt_data.get("pros", []),
                        cons=alt_data.get("cons", []),
                        risk_level=self._parse_risk_level(alt_data.get("risk_level", "medium")),
                        estimated_time=int(alt_data.get("estimated_time", 0)),
                        compatibility=alt_data.get("compatibility", {})
                    )
                    alternatives.append(alternative)

                # 创建修复建议对象
                suggestion = AIFixSuggestion(
                    suggestion_id=suggestion_item["suggestion_id"],
                    problem_id=problem.original_problem.problem_id,
                    file_path=problem.original_problem.file_path,
                    line_number=problem.original_problem.line_number,
                    original_code=suggestion_item["original_code"],
                    suggested_code=suggestion_item["suggested_code"],
                    explanation=suggestion_item["explanation"],
                    reasoning=suggestion_item["reasoning"],
                    confidence=confidence,
                    risk_level=risk_level,
                    side_effects=suggestion_item.get("side_effects", []),
                    alternatives=alternatives,
                    estimated_impact=suggestion_item.get("estimated_impact", ""),
                    fix_type=fix_type,
                    dependencies=suggestion_item.get("dependencies", []),
                    testing_requirements=suggestion_item.get("testing_requirements", [])
                )

                suggestions.append(suggestion)

            except Exception as e:
                self.logger.warning(f"解析修复建议数据失败: {e}")
                continue

        return suggestions

    def _parse_risk_level(self, risk_str: str) -> RiskLevel:
        """解析风险等级"""
        level_mapping = {
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH
        }

        risk_lower = risk_str.lower()
        return level_mapping.get(risk_lower, RiskLevel.MEDIUM)

    def _parse_fix_type(self, fix_type_str: str) -> FixType:
        """解析修复类型"""
        type_mapping = {
            "code_replacement": FixType.CODE_REPLACEMENT,
            "code_insertion": FixType.CODE_INSERTION,
            "code_deletion": FixType.CODE_DELETION,
            "refactoring": FixType.REFACTORING,
            "configuration": FixType.CONFIGURATION,
            "dependency_update": FixType.DEPENDENCY_UPDATE
        }

        fix_type_lower = fix_type_str.lower()
        return type_mapping.get(fix_type_lower, FixType.CODE_REPLACEMENT)

    def _validate_and_optimize_suggestions(self,
                                         suggestions: List[AIFixSuggestion],
                                         suggestion_context: FixSuggestionContext) -> List[AIFixSuggestion]:
        """验证和优化建议"""
        if not suggestions:
            return suggestions

        validated_suggestions = []

        for suggestion in suggestions:
            try:
                # 验证建议质量
                if self._validate_suggestion_quality(suggestion, suggestion_context):
                    # 优化建议
                    optimized_suggestion = self._optimize_suggestion(suggestion, suggestion_context)
                    validated_suggestions.append(optimized_suggestion)
                else:
                    self.logger.debug(f"过滤低质量建议: {suggestion.suggestion_id}")

            except Exception as e:
                self.logger.warning(f"验证建议失败 {suggestion.suggestion_id}: {e}")
                continue

        # 按置信度和风险等级排序
        validated_suggestions.sort(
            key=lambda s: (
                s.confidence,
                self._get_risk_weight(s.risk_level) * -1,  # 风险越高权重越大，但排序时优先级靠前
                len(s.explanation)  # 描述越详细越好
            ),
            reverse=True
        )

        return validated_suggestions

    def _validate_suggestion_quality(self,
                                    suggestion: AIFixSuggestion,
                                    suggestion_context: FixSuggestionContext) -> bool:
        """验证建议质量"""
        # 检查基本字段
        if not suggestion.suggested_code or len(suggestion.suggested_code.strip()) < 5:
            return False

        if not suggestion.explanation or len(suggestion.explanation.strip()) < 10:
            return False

        if not suggestion.reasoning or len(suggestion.reasoning.strip()) < 20:
            return False

        # 检查置信度
        if suggestion.confidence < self.generation_config["min_confidence"]:
            return False

        # 检查修复约束
        constraints = suggestion_context.fix_constraints

        # 如果不允许破坏性变更，检查是否有破坏性变更
        if not constraints.get("allow_breaking_changes", False):
            if self._has_breaking_changes(suggestion):
                return False

        # 如果偏好最小变更，检查变更幅度
        if constraints.get("prefer_minimal_changes", True):
            if not self._is_minimal_change(suggestion):
                return False

        return True

    def _has_breaking_changes(self, suggestion: AIFixSuggestion) -> bool:
        """检查是否有破坏性变更"""
        # 简单的启发式检查
        breaking_keywords = [
            "remove", "delete", "deprecate", "replace entire",
            "change signature", "modify interface", "break compatibility"
        ]

        text_to_check = (suggestion.explanation + " " + suggestion.reasoning).lower()
        return any(keyword in text_to_check for keyword in breaking_keywords)

    def _is_minimal_change(self, suggestion: AIFixSuggestion) -> bool:
        """检查是否为最小变更"""
        # 简单的启发式检查
        original_lines = len(suggestion.original_code.split('\n'))
        suggested_lines = len(suggestion.suggested_code.split('\n'))

        # 如果建议代码行数增加超过50%，可能不是最小变更
        if suggested_lines > original_lines * 1.5:
            return False

        return True

    def _optimize_suggestion(self,
                            suggestion: AIFixSuggestion,
                            suggestion_context: FixSuggestionContext) -> AIFixSuggestion:
        """优化建议"""
        # 优化解释和推理
        suggestion.explanation = self._optimize_text(suggestion.explanation, max_length=300)
        suggestion.reasoning = self._optimize_text(suggestion.reasoning, max_length=500)

        # 优化副作用描述
        suggestion.side_effects = [self._optimize_text(effect, max_length=100)
                                 for effect in suggestion.side_effects[:3]]  # 限制副作用数量

        # 优化替代方案
        suggestion.alternatives = suggestion.alternatives[:self.generation_config["max_alternatives"]]

        return suggestion

    def _optimize_text(self, text: str, max_length: int = 200) -> str:
        """优化文本长度"""
        if len(text) <= max_length:
            return text

        # 截断并添加省略号
        truncated = text[:max_length - 3].rstrip()
        return truncated + "..."

    def _get_risk_weight(self, risk_level: RiskLevel) -> int:
        """获取风险权重"""
        weights = {
            RiskLevel.HIGH: 3,
            RiskLevel.MEDIUM: 2,
            RiskLevel.LOW: 1
        }
        return weights.get(risk_level, 2)

    def _generate_suggestion_summary(self,
                                   suggestions: List[AIFixSuggestion],
                                   suggestion_context: FixSuggestionContext) -> Dict[str, Any]:
        """生成建议摘要"""
        if not suggestions:
            return {
                "total_suggestions": 0,
                "risk_distribution": {},
                "confidence_stats": {},
                "average_confidence": 0,
                "high_risk_suggestions": 0
            }

        # 统计信息
        risk_counts = {}
        confidence_values = []
        type_counts = {}
        total_fix_time = 0

        for suggestion in suggestions:
            # 风险分布
            risk = suggestion.risk_level.value
            risk_counts[risk] = risk_counts.get(risk, 0) + 1

            # 置信度统计
            confidence_values.append(suggestion.confidence)

            # 修复类型分布
            fix_type = suggestion.fix_type.value
            type_counts[fix_type] = type_counts.get(fix_type, 0) + 1

        # 计算统计指标
        avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0

        summary = {
            "total_suggestions": len(suggestions),
            "risk_distribution": risk_counts,
            "type_distribution": type_counts,
            "confidence_stats": {
                "average": round(avg_confidence, 3),
                "min": round(min(confidence_values), 3) if confidence_values else 0,
                "max": round(max(confidence_values), 3) if confidence_values else 0
            },
            "average_confidence": round(avg_confidence, 3),
            "high_risk_suggestions": risk_counts.get("high", 0),
            "medium_risk_suggestions": risk_counts.get("medium", 0),
            "low_risk_suggestions": risk_counts.get("low", 0),
            "suggestions_with_alternatives": sum(1 for s in suggestions if s.alternatives),
            "suggestions_with_testing_requirements": sum(1 for s in suggestions if s.testing_requirements)
        }

        return summary

    def _generate_suggestion_id(self) -> str:
        """生成建议ID"""
        import uuid
        return f"suggestion_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"


# 便捷函数
def generate_fix_suggestions(suggestion_context: Dict[str, Any],
                            focus_problems: Optional[List[str]] = None,
                            llm_client: Any = None) -> Dict[str, Any]:
    """
    便捷的修复建议生成函数

    Args:
        suggestion_context: 修复建议上下文
        focus_problems: 重点问题列表
        llm_client: LLM客户端实例

    Returns:
        Dict[str, Any]: 生成结果
    """
    # 重建上下文对象（简化实现）
    generator = AIFixSuggestionGenerator(llm_client)

    # 这里应该重建完整的FixSuggestionContext对象
    # 为了简化，直接使用字典数据
    context = suggestion_context

    result = generator.generate_suggestions(context, focus_problems)

    return result.to_dict()