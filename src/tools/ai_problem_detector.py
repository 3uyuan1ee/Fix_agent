"""
AI问题检测执行器 - T008.2
执行AI问题检测
"""

import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..utils.logger import get_logger
try:
    from .problem_detection_context_builder import ProblemDetectionContext
    from .workflow_data_types import AIDetectedProblem, ProblemType, SeverityLevel, FixType, CodeContext
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

    @dataclass
    class CodeContext:
        file_path: str
        line_number: int
        function_name: Optional[str] = None
        class_name: Optional[str] = None
        surrounding_lines: List[str] = field(default_factory=list)
        imports: List[str] = field(default_factory=list)

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
        context: Optional[CodeContext] = None
        tags: List[str] = field(default_factory=list)
        estimated_fix_time: int = 0
        detection_timestamp: datetime = field(default_factory=datetime.now)

    @dataclass
    class ProblemDetectionContext:
        context_id: str
        project_info: Dict[str, Any]
        selected_files: List[Dict[str, Any]]
        static_analysis_results: Dict[str, Any]
        file_contents: Dict[str, str] = field(default_factory=dict)
        code_contexts: Dict[str, Any] = field(default_factory=dict)
        user_preferences: Dict[str, Any] = field(default_factory=dict)
        detection_focus: List[str] = field(default_factory=list)
        context_statistics: Dict[str, Any] = field(default_factory=dict)
        build_timestamp: str = ""
        token_estimate: int = 0

    class UnifiedLLMClient:
        def __init__(self, *args, **kwargs):
            pass

        def chat_completion(self, *args, **kwargs):
            return {"content": '{"detected_problems": []}', "success": True}


@dataclass
class ProblemDetectionResult:
    """问题检测结果"""
    detection_id: str
    context_id: str
    detected_problems: List[AIDetectedProblem] = field(default_factory=list)
    detection_summary: Dict[str, Any] = field(default_factory=dict)
    execution_success: bool = True
    execution_time: float = 0.0
    error_message: str = ""
    ai_responses: List[Dict[str, Any]] = field(default_factory=list)
    token_usage: Dict[str, int] = field(default_factory=dict)
    detection_timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "detection_id": self.detection_id,
            "context_id": self.context_id,
            "detected_problems": [problem.to_dict() for problem in self.detected_problems],
            "detection_summary": self.detection_summary,
            "execution_success": self.execution_success,
            "execution_time": self.execution_time,
            "error_message": self.error_message,
            "ai_responses": self.ai_responses,
            "token_usage": self.token_usage,
            "detection_timestamp": self.detection_timestamp,
            "total_problems": len(self.detected_problems)
        }


class AIProblemDetector:
    """AI问题检测执行器"""

    def __init__(self,
                 llm_client: Optional[Any] = None,
                 max_concurrent_analyses: int = 3,
                 max_retries: int = 3,
                 retry_delay: float = 1.0):
        self.llm_client = llm_client
        self.max_concurrent_analyses = max_concurrent_analyses
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = get_logger()

        # 检测配置
        self.detection_config = {
            "temperature": 0.3,  # 较低温度以获得一致的结果
            "max_tokens": 2000,  # 每次AI调用的最大token数
            "timeout": 60,  # 单次AI调用超时时间（秒）
            "min_confidence": 0.5,  # 最小置信度阈值
            "max_problems_per_file": 10,  # 每个文件最大问题数
            "focus_areas": [
                "security", "performance", "logic", "maintainability",
                "reliability", "best_practices", "error_handling"
            ]
        }

        # 系统提示词模板
        self.system_prompt_template = """
你是一个专业的代码质量分析专家，擅长发现静态分析工具可能遗漏的深层代码问题。

你的任务是分析提供的代码上下文，发现以下类型的问题：
1. **安全问题**: 安全漏洞、输入验证不足、权限控制缺陷等
2. **性能问题**: 性能瓶颈、资源泄漏、算法效率问题等
3. **逻辑问题**: 业务逻辑错误、边界条件处理、状态管理问题等
4. **可维护性问题**: 代码结构混乱、重复代码、命名不当等
5. **可靠性问题**: 错误处理不足、异常情况未考虑、资源管理问题等
6. **最佳实践问题**: 违反编程最佳实践、设计模式误用等

分析要求：
- 重点关注静态分析工具可能遗漏的深层问题
- 提供具体的问题位置和代码片段
- 给出详细的问题描述和影响分析
- 评估问题的严重程度和置信度
- 提供问题产生的原因分析

输出格式：
严格按照JSON格式输出，包含detected_problems数组，每个问题包含：
- problem_id: 问题唯一标识
- file_path: 文件路径
- line_number: 行号
- problem_type: 问题类型
- severity: 严重程度 (low/medium/high/critical)
- description: 问题描述
- code_snippet: 问题代码片段
- confidence: 置信度 (0.0-1.0)
- reasoning: 推理过程
- suggested_fix_type: 建议修复类型
- estimated_fix_time: 预估修复时间（分钟）
"""

    def detect_problems(self,
                       detection_context: ProblemDetectionContext,
                       focus_files: Optional[List[str]] = None) -> ProblemDetectionResult:
        """
        执行AI问题检测

        Args:
            detection_context: 问题检测上下文
            focus_files: 重点分析的文件列表（可选）

        Returns:
            ProblemDetectionResult: 检测结果
        """
        start_time = time.time()
        self.logger.info(f"开始AI问题检测，上下文ID: {detection_context.context_id}")

        result = ProblemDetectionResult(
            detection_id=self._generate_detection_id(),
            context_id=detection_context.context_id,
            detection_timestamp=datetime.now().isoformat()
        )

        try:
            # 确定要分析的文件
            files_to_analyze = self._select_files_for_analysis(
                detection_context.selected_files, focus_files
            )

            self.logger.info(f"选择 {len(files_to_analyze)} 个文件进行AI分析")

            # 并行执行文件分析
            detected_problems = self._analyze_files_parallel(
                files_to_analyze, detection_context
            )

            # 去重和验证问题
            result.detected_problems = self._deduplicate_and_validate_problems(detected_problems)

            # 生成检测摘要
            result.detection_summary = self._generate_detection_summary(
                result.detected_problems, detection_context
            )

            # 计算执行时间
            result.execution_time = time.time() - start_time

            self.logger.info(
                f"AI问题检测完成: 发现 {len(result.detected_problems)} 个问题, "
                f"耗时 {result.execution_time:.2f}秒"
            )

        except Exception as e:
            result.execution_success = False
            result.error_message = f"AI问题检测执行失败: {e}"
            result.execution_time = time.time() - start_time
            self.logger.error(result.error_message)

        return result

    def _select_files_for_analysis(self,
                                 selected_files: List[Dict[str, Any]],
                                 focus_files: Optional[List[str]]) -> List[Dict[str, Any]]:
        """选择要分析的文件"""
        if focus_files:
            # 如果指定了重点文件，只分析这些文件
            focused_files = []
            for file_data in selected_files:
                if file_data.get("file_path") in focus_files:
                    focused_files.append(file_data)
            return focused_files

        # 否则按优先级选择，最多分析20个文件
        priority_weights = {"high": 3, "medium": 2, "low": 1}
        sorted_files = sorted(
            selected_files,
            key=lambda x: (
                priority_weights.get(x.get("priority", "medium"), 2),
                x.get("analysis_priority", 0)
            ),
            reverse=True
        )

        return sorted_files[:20]

    def _analyze_files_parallel(self,
                              files_to_analyze: List[Dict[str, Any]],
                              detection_context: ProblemDetectionContext) -> List[AIDetectedProblem]:
        """并行分析文件"""
        all_problems = []

        with ThreadPoolExecutor(max_workers=self.max_concurrent_analyses) as executor:
            # 提交分析任务
            future_to_file = {}
            for file_data in files_to_analyze:
                future = executor.submit(
                    self._analyze_single_file,
                    file_data,
                    detection_context
                )
                future_to_file[future] = file_data

            # 收集结果
            for future in as_completed(future_to_file):
                file_data = future_to_file[future]
                try:
                    file_problems = future.result(timeout=120)
                    all_problems.extend(file_problems)
                    self.logger.info(
                        f"文件 {file_data.get('relative_path', 'unknown')} "
                        f"分析完成，发现 {len(file_problems)} 个问题"
                    )
                except Exception as e:
                    self.logger.error(
                        f"文件 {file_data.get('relative_path', 'unknown')} "
                        f"分析失败: {e}"
                    )

        return all_problems

    def _analyze_single_file(self,
                            file_data: Dict[str, Any],
                            detection_context: ProblemDetectionContext) -> List[AIDetectedProblem]:
        """分析单个文件"""
        file_path = file_data.get("file_path", "")
        relative_path = file_data.get("relative_path", file_path)

        if not file_path:
            return []

        self.logger.debug(f"开始分析文件: {relative_path}")

        # 构建文件分析提示词
        user_prompt = self._build_file_analysis_prompt(file_data, detection_context)

        # 调用AI进行分析
        ai_response = self._call_ai_with_retry(user_prompt)

        if not ai_response.get("success", False):
            self.logger.warning(f"AI分析失败: {ai_response.get('error_message', '未知错误')}")
            return []

        # 解析AI响应
        try:
            response_content = ai_response.get("content", "")
            detection_data = json.loads(response_content)

            # 转换为AIDetectedProblem对象
            problems = self._parse_ai_problems(detection_data, file_path, detection_context)

            # 限制每个文件的问题数量
            if len(problems) > self.detection_config["max_problems_per_file"]:
                problems = sorted(problems, key=lambda p: p.confidence, reverse=True)
                problems = problems[:self.detection_config["max_problems_per_file"]]

            return problems

        except json.JSONDecodeError as e:
            self.logger.error(f"解析AI响应失败 {relative_path}: {e}")
            return []

    def _build_file_analysis_prompt(self,
                                  file_data: Dict[str, Any],
                                  detection_context: ProblemDetectionContext) -> str:
        """构建文件分析提示词"""
        file_path = file_data.get("file_path", "")
        relative_path = file_data.get("relative_path", file_path)
        language = file_data.get("language", "unknown")

        # 获取文件内容
        file_content = detection_context.file_contents.get(file_path, "")

        # 获取静态分析结果
        static_issues = []
        if file_path in detection_context.static_analysis_results:
            result = detection_context.static_analysis_results[file_path]
            static_issues = result.get("issues", [])[:5]  # 限制静态问题数量

        # 获取代码上下文
        code_contexts = detection_context.code_contexts.get(file_path, [])

        # 构建用户提示词
        prompt_parts = [
            f"# 文件分析任务",
            f"",
            f"## 文件信息",
            f"- 文件路径: {relative_path}",
            f"- 编程语言: {language}",
            f"- 优先级: {file_data.get('priority', 'medium')}",
            f"- AI选择理由: {file_data.get('ai_selection_reason', '')}",
            f"- 预期修复数量: {file_data.get('expected_fixes', 0)}",
            f"",
            f"## 项目上下文",
            f"- 项目类型: {detection_context.project_info.get('project_type', '未知')}",
            f"- 项目复杂度: {detection_context.project_info.get('complexity_level', '中')}",
            f"- 检测重点: {', '.join(detection_context.detection_focus)}",
            f"",
            f"## 静态分析结果",
            f"已知问题（来自静态分析工具）："
        ]

        if static_issues:
            for i, issue in enumerate(static_issues, 1):
                prompt_parts.append(
                    f"{i}. 行{issue.get('line_number', '?')}: "
                    f"{issue.get('message', '未知问题')} "
                    f"[{issue.get('severity', 'unknown')}]"
                )
        else:
            prompt_parts.append("- 无已知问题")

        prompt_parts.extend([
            f"",
            f"## 文件内容",
            f"```{language}",
            file_content[:3000],  # 限制内容长度
            "```" if len(file_content) > 3000 else "",
            f"",
            f"## 分析要求",
            f"请深入分析以上代码，重点发现：",
            f"1. 静态分析工具可能遗漏的深层问题",
            f"2. 业务逻辑和架构层面的问题",
            f"3. 安全性和性能隐患",
            f"4. 可维护性和可靠性问题",
            f"",
            f"注意：",
            f"- 不要重复静态分析已经发现的问题",
            f"- 重点关注代码逻辑、设计模式、异常处理等方面",
            f"- 提供具体的问题位置和改进建议",
            f"- 评估问题的严重程度和修复难度",
            f"",
            f"请以JSON格式输出分析结果。"
        ])

        return "\n".join(prompt_parts)

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
                    "temperature": self.detection_config["temperature"],
                    "max_tokens": self.detection_config["max_tokens"],
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

    def _parse_ai_problems(self,
                          detection_data: Dict[str, Any],
                          file_path: str,
                          detection_context: ProblemDetectionContext) -> List[AIDetectedProblem]:
        """解析AI检测到的问题"""
        problems = []
        detected_problems = detection_data.get("detected_problems", [])

        for problem_data in detected_problems:
            try:
                # 验证必需字段
                if not all(key in problem_data for key in [
                    "problem_id", "line_number", "problem_type", "severity",
                    "description", "code_snippet", "confidence", "reasoning"
                ]):
                    continue

                # 解析问题类型
                problem_type = self._parse_problem_type(problem_data.get("problem_type", ""))
                if not problem_type:
                    continue

                # 解析严重程度
                severity = self._parse_severity_level(problem_data.get("severity", ""))
                if not severity:
                    continue

                # 解析修复类型
                fix_type = self._parse_fix_type(problem_data.get("suggested_fix_type", ""))

                # 验证置信度
                confidence = float(problem_data.get("confidence", 0.0))
                if confidence < self.detection_config["min_confidence"]:
                    continue

                # 创建问题对象
                problem = AIDetectedProblem(
                    problem_id=problem_data["problem_id"],
                    file_path=file_path,
                    line_number=int(problem_data["line_number"]),
                    problem_type=problem_type,
                    severity=severity,
                    description=problem_data["description"],
                    code_snippet=problem_data["code_snippet"],
                    confidence=confidence,
                    reasoning=problem_data["reasoning"],
                    suggested_fix_type=fix_type,
                    estimated_fix_time=int(problem_data.get("estimated_fix_time", 30)),
                    tags=problem_data.get("tags", [])
                )

                problems.append(problem)

            except Exception as e:
                self.logger.warning(f"解析问题数据失败: {e}")
                continue

        return problems

    def _parse_problem_type(self, problem_type_str: str) -> Optional[ProblemType]:
        """解析问题类型"""
        type_mapping = {
            "security": ProblemType.SECURITY,
            "performance": ProblemType.PERFORMANCE,
            "logic": ProblemType.LOGIC,
            "style": ProblemType.STYLE,
            "maintainability": ProblemType.MAINTAINABILITY,
            "reliability": ProblemType.RELIABILITY,
            "compatibility": ProblemType.COMPATIBILITY,
            "documentation": ProblemType.DOCUMENTATION
        }

        problem_type_lower = problem_type_str.lower()
        return type_mapping.get(problem_type_lower)

    def _parse_severity_level(self, severity_str: str) -> Optional[SeverityLevel]:
        """解析严重程度"""
        level_mapping = {
            "low": SeverityLevel.LOW,
            "medium": SeverityLevel.MEDIUM,
            "high": SeverityLevel.HIGH,
            "critical": SeverityLevel.CRITICAL
        }

        severity_lower = severity_str.lower()
        return level_mapping.get(severity_lower)

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

    def _deduplicate_and_validate_problems(self, problems: List[AIDetectedProblem]) -> List[AIDetectedProblem]:
        """去重和验证问题"""
        if not problems:
            return []

        # 按文件路径和行号去重
        seen_problems = set()
        deduplicated_problems = []

        for problem in problems:
            # 创建去重键
            dedup_key = (problem.file_path, problem.line_number, problem.problem_type, problem.description[:100])

            if dedup_key not in seen_problems:
                seen_problems.add(dedup_key)
                deduplicated_problems.append(problem)

        # 验证问题质量
        validated_problems = []
        for problem in deduplicated_problems:
            if self._validate_problem_quality(problem):
                validated_problems.append(problem)

        # 按严重程度和置信度排序
        validated_problems.sort(
            key=lambda p: (
                self._get_severity_weight(p.severity),
                p.confidence
            ),
            reverse=True
        )

        return validated_problems

    def _validate_problem_quality(self, problem: AIDetectedProblem) -> bool:
        """验证问题质量"""
        # 检查基本字段
        if not problem.description or len(problem.description.strip()) < 10:
            return False

        if not problem.code_snippet or len(problem.code_snippet.strip()) < 5:
            return False

        if not problem.reasoning or len(problem.reasoning.strip()) < 20:
            return False

        # 检查行号合理性
        if problem.line_number <= 0:
            return False

        return True

    def _get_severity_weight(self, severity: SeverityLevel) -> float:
        """获取严重程度权重"""
        weights = {
            SeverityLevel.CRITICAL: 4.0,
            SeverityLevel.HIGH: 3.0,
            SeverityLevel.MEDIUM: 2.0,
            SeverityLevel.LOW: 1.0
        }
        return weights.get(severity, 1.0)

    def _generate_detection_summary(self,
                                   problems: List[AIDetectedProblem],
                                   detection_context: ProblemDetectionContext) -> Dict[str, Any]:
        """生成检测摘要"""
        if not problems:
            return {
                "total_problems": 0,
                "severity_distribution": {},
                "type_distribution": {},
                "file_distribution": {},
                "confidence_stats": {},
                "estimated_fix_time_total": 0
            }

        # 统计信息
        severity_counts = {}
        type_counts = {}
        file_counts = {}
        confidence_values = []

        total_fix_time = 0

        for problem in problems:
            # 严重程度分布
            severity_counts[problem.severity.value] = severity_counts.get(problem.severity.value, 0) + 1

            # 问题类型分布
            type_counts[problem.problem_type.value] = type_counts.get(problem.problem_type.value, 0) + 1

            # 文件分布
            file_counts[problem.file_path] = file_counts.get(problem.file_path, 0) + 1

            # 置信度统计
            confidence_values.append(problem.confidence)

            # 修复时间
            total_fix_time += problem.estimated_fix_time

        # 计算统计指标
        avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0

        summary = {
            "total_problems": len(problems),
            "severity_distribution": severity_counts,
            "type_distribution": type_counts,
            "file_distribution": dict(sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "confidence_stats": {
                "average": round(avg_confidence, 3),
                "min": round(min(confidence_values), 3) if confidence_values else 0,
                "max": round(max(confidence_values), 3) if confidence_values else 0
            },
            "estimated_fix_time_total": total_fix_time,
            "estimated_fix_time_hours": round(total_fix_time / 60, 2),
            "high_priority_files": [file for file, count in file_counts.items() if count >= 3]
        }

        return summary

    def _generate_detection_id(self) -> str:
        """生成检测ID"""
        import uuid
        return f"detection_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"


# 便捷函数
def detect_problems_with_ai(detection_context: Dict[str, Any],
                           focus_files: Optional[List[str]] = None,
                           llm_client: Any = None) -> Dict[str, Any]:
    """
    便捷的AI问题检测函数

    Args:
        detection_context: 问题检测上下文
        focus_files: 重点分析文件列表
        llm_client: LLM客户端实例

    Returns:
        Dict[str, Any]: 检测结果
    """
    # 重建上下文对象（简化实现）
    from .problem_detection_context_builder import ProblemDetectionContextBuilder
    builder = ProblemDetectionContextBuilder()

    # 这里应该重建完整的ProblemDetectionContext对象
    # 为了简化，直接使用字典数据
    context = detection_context

    detector = AIProblemDetector(llm_client)
    result = detector.detect_problems(context, focus_files)

    return result.to_dict()