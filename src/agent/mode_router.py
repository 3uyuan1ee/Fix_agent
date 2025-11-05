"""
模式切换和路由模块
实现三种分析模式的识别、切换和请求路由功能
"""

import re
from dataclasses import dataclass, field
from enum import Enum

# 使用字符串类型定义避免循环导入
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from ..utils.config import get_config_manager
from ..utils.logger import get_logger
from .planner import AnalysisMode, ExecutionPlan, UserRequest

if TYPE_CHECKING:
    from .orchestrator import Session, SessionState


def _get_session_state():
    """延迟导入SessionState枚举"""
    from .orchestrator import SessionState

    return SessionState


@dataclass
class RouteRequest:
    """路由请求数据结构"""

    user_input: str
    session: "Session"  # 使用字符串类型避免循环导入
    context: Dict[str, Any] = field(default_factory=dict)
    force_mode: Optional[AnalysisMode] = None
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RouteResult:
    """路由结果数据结构"""

    success: bool
    mode: AnalysisMode
    execution_method: str  # "direct", "interactive", "confirmation"
    execution_plan: Optional[ExecutionPlan] = None
    response_message: str = ""
    next_state: Optional["SessionState"] = None  # 延迟设置默认值
    error: Optional[str] = None
    error_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理，设置默认的next_state"""
        if self.next_state is None:
            SessionState = _get_session_state()
            self.next_state = SessionState.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "mode": self.mode.value,
            "execution_method": self.execution_method,
            "execution_plan_id": (
                self.execution_plan.plan_id if self.execution_plan else None
            ),
            "response_message": self.response_message,
            "next_state": self.next_state.value if self.next_state else None,
            "error": self.error,
            "error_type": self.error_type,
            "metadata": self.metadata,
        }


class ModeRecognizer:
    """模式识别器"""

    def __init__(self, config_manager=None):
        """
        初始化模式识别器

        Args:
            config_manager: 配置管理器实例
        """
        self.logger = get_logger()
        self.config_manager = config_manager or get_config_manager()

        # 获取配置
        try:
            self.config = self.config_manager.get_section("mode_recognizer") or {}
        except:
            self.config = {}

        # 模式识别关键词
        self.static_keywords = self.config.get(
            "static_keywords",
            [
                "static",
                "quick",
                "fast",
                "basic",
                "simple",
                "check",
                "scan",
                "test",
                "静态",
                "快速",
                "基础",
                "简单",
                "检查",
                "扫描",
                "测试",
                "校验",
                "验证",
            ],
        )

        self.deep_keywords = self.config.get(
            "deep_keywords",
            [
                "deep",
                "detailed",
                "thorough",
                "comprehensive",
                "analyze",
                "analysis",
                "review",
                "深度",
                "详细",
                "全面",
                "智能",
                "分析",
                "解析",
                "解释",
                "说明",
                "架构",
                "设计",
                "原理",
                "实现",
                "逻辑",
            ],
        )

        self.fix_keywords = self.config.get(
            "fix_keywords",
            [
                "fix",
                "repair",
                "resolve",
                "correct",
                "auto-fix",
                "fixing",
                "debug",
                "patch",
                "修复",
                "解决",
                "更正",
                "自动修复",
                "调试",
                "补丁",
                "改正",
                "缺陷",
                "错误",
                "异常",
                "问题",
                "优化",
                "改进",
            ],
        )

        # 命令模式关键词
        self.command_patterns = [
            r"^(static|analyze|check|scan)\s+",
            r"^(deep|detailed|thorough)\s+",
            r"^(fix|repair|resolve)\s+",
            r"^/(static|deep|fix|analyze|scan|repair|review)\s*",
            r"--mode\s*=\s*(static|deep|fix)",
            r"-m\s+(static|deep|fix)",
        ]

        self.logger.info("ModeRecognizer initialized")

    def recognize_mode(
        self,
        user_input: str,
        session: Optional["Session"] = None,
        force_mode: Optional[AnalysisMode] = None,
    ) -> Tuple[AnalysisMode, float]:
        """
        识别用户输入的分析模式

        Args:
            user_input: 用户输入
            session: 当前会话（可选）
            force_mode: 强制指定的模式（可选）

        Returns:
            (识别的模式, 置信度)
        """
        # 如果强制指定了模式，直接返回
        if force_mode:
            return force_mode, 1.0

        input_lower = user_input.lower().strip()

        # 检查命令模式
        command_mode = self._check_command_pattern(input_lower)
        if command_mode:
            return command_mode, 0.95

        # 检查上下文模式（基于会话历史）
        if session and session.messages:
            context_mode = self._check_context_mode(session)
            if context_mode:
                return context_mode, 0.80

        # 基于关键词识别
        mode_scores = self._calculate_mode_scores(input_lower)

        # 选择得分最高的模式
        if mode_scores:
            best_mode, best_score = max(mode_scores.items(), key=lambda x: x[1])

            # 如果得分太低（没有关键词匹配），使用默认模式
            if best_score == 0:
                return AnalysisMode.STATIC, 0.5

            # 计算置信度：基于匹配的关键词数量
            confidence = min(
                0.5 + (best_score * 0.2), 1.0
            )  # 基础0.5 + 每个0.2，最高1.0
            return best_mode, confidence

        # 默认使用静态分析
        return AnalysisMode.STATIC, 0.5

    def _check_command_pattern(self, user_input: str) -> Optional[AnalysisMode]:
        """检查命令模式"""
        for pattern in self.command_patterns:
            match = re.search(pattern, user_input)
            if match:
                mode_str = match.group(1) if match.groups() else match.group(0)
                mode_str = mode_str.lower()

                if mode_str in ["static", "check", "scan", "analyze", "review"]:
                    return (
                        AnalysisMode.STATIC
                        if mode_str != "review"
                        else AnalysisMode.DEEP
                    )
                elif mode_str in ["deep", "detailed", "comprehensive", "review"]:
                    return AnalysisMode.DEEP
                elif mode_str in ["fix", "repair", "resolve"]:
                    return AnalysisMode.FIX

        return None

    def _check_context_mode(self, session: "Session") -> Optional[AnalysisMode]:
        """基于会话上下文检查模式"""
        if not session.messages:
            return None

        # 检查最近的消息中是否有模式指示
        recent_messages = session.messages[-5:]  # 最近5条消息

        mode_counts = {
            AnalysisMode.STATIC: 0,
            AnalysisMode.DEEP: 0,
            AnalysisMode.FIX: 0,
        }

        for message in recent_messages:
            content = message.content.lower()

            if any(keyword in content for keyword in self.static_keywords):
                mode_counts[AnalysisMode.STATIC] += 2
            if any(keyword in content for keyword in self.deep_keywords):
                mode_counts[AnalysisMode.DEEP] += 2
            if any(keyword in content for keyword in self.fix_keywords):
                mode_counts[AnalysisMode.FIX] += 2

        # 如果有明显的模式偏好，返回该模式
        max_count = max(mode_counts.values())
        if max_count >= 4:  # 至少有2条相关消息
            return max(mode_counts, key=mode_counts.get)

        return None

    def _calculate_mode_scores(self, user_input: str) -> Dict[AnalysisMode, float]:
        """计算各模式的得分"""
        scores = {}

        # 静态分析得分
        static_matches = sum(
            1 for keyword in self.static_keywords if keyword in user_input
        )
        scores[AnalysisMode.STATIC] = static_matches

        # 深度分析得分
        deep_matches = sum(1 for keyword in self.deep_keywords if keyword in user_input)
        scores[AnalysisMode.DEEP] = deep_matches

        # 修复分析得分
        fix_matches = sum(1 for keyword in self.fix_keywords if keyword in user_input)
        scores[AnalysisMode.FIX] = fix_matches

        return scores

    def get_mode_suggestions(
        self, user_input: str, top_n: int = 3
    ) -> List[Tuple[AnalysisMode, float]]:
        """
        获取模式建议

        Args:
            user_input: 用户输入
            top_n: 返回前N个建议

        Returns:
            模式建议列表 [(模式, 置信度), ...]
        """
        mode, confidence = self.recognize_mode(user_input)

        # 获取所有模式的得分
        input_lower = user_input.lower().strip()
        mode_scores = self._calculate_mode_scores(input_lower)

        # 确保当前识别的模式在列表中
        if mode not in mode_scores:
            mode_scores[mode] = confidence

        # 按得分排序
        sorted_modes = sorted(mode_scores.items(), key=lambda x: x[1], reverse=True)

        return sorted_modes[:top_n]


class RequestRouter:
    """请求路由器"""

    def __init__(self, config_manager=None, task_planner=None, execution_engine=None):
        """
        初始化请求路由器

        Args:
            config_manager: 配置管理器实例
            task_planner: 任务规划器实例
            execution_engine: 执行引擎实例
        """
        self.logger = get_logger()
        self.config_manager = config_manager or get_config_manager()

        # 初始化组件
        self.mode_recognizer = ModeRecognizer(config_manager)
        self.task_planner = task_planner
        self.execution_engine = execution_engine

        # 获取配置
        try:
            self.config = self.config_manager.get_section("request_router") or {}
        except:
            self.config = {}

        # 路由配置
        self.auto_execute_static = self.config.get("auto_execute_static", True)
        self.interactive_deep = self.config.get("interactive_deep", True)
        self.confirmation_fix = self.config.get("confirmation_fix", True)

        # 路由处理器
        self.route_handlers = {
            AnalysisMode.STATIC: self._handle_static_route,
            AnalysisMode.DEEP: self._handle_deep_route,
            AnalysisMode.FIX: self._handle_fix_route,
        }

        self.logger.info("RequestRouter initialized")

    def route_request(self, route_request: RouteRequest) -> RouteResult:
        """
        路由用户请求

        Args:
            route_request: 路由请求

        Returns:
            路由结果
        """
        self.logger.info(f"Routing request: {route_request.user_input[:50]}...")

        try:
            # 识别模式
            mode, confidence = self.mode_recognizer.recognize_mode(
                route_request.user_input,
                route_request.session,
                route_request.force_mode,
            )

            self.logger.info(
                f"Recognized mode: {mode.value} (confidence: {confidence:.2f})"
            )

            # 获取对应的处理器
            handler = self.route_handlers.get(mode)
            if not handler:
                return RouteResult(
                    success=False,
                    mode=mode,
                    execution_method="unknown",
                    error=f"No handler for mode: {mode.value}",
                    error_type="NoHandlerError",
                )

            # 执行路由处理
            return handler(route_request, confidence)

        except Exception as e:
            self.logger.error(f"Error routing request: {e}")
            return RouteResult(
                success=False,
                mode=AnalysisMode.STATIC,  # 默认模式
                execution_method="error",
                error=str(e),
                error_type=type(e).__name__,
            )

    def _handle_static_route(
        self, route_request: RouteRequest, confidence: float
    ) -> RouteResult:
        """处理静态分析路由"""
        session = route_request.session
        user_input = route_request.user_input

        # 获取SessionState
        SessionState = _get_session_state()

        # 更新会话状态
        session.update_state(
            SessionState.PROCESSING,
            {"routing_mode": "static", "confidence": confidence},
        )

        # 添加用户消息
        user_message = session.add_message(
            "user", user_input, {"mode": "static", "routing_confidence": confidence}
        )

        try:
            # 解析用户请求
            current_path = route_request.context.get("current_path", ".")
            user_request = self.task_planner.parse_user_request(
                user_input, current_path
            )
            user_request.mode = AnalysisMode.STATIC  # 确保模式正确

            # 创建执行计划
            execution_plan = self.task_planner.create_execution_plan(user_request)
            session.current_request = user_request
            session.current_plan = execution_plan

            # 验证计划
            is_valid, errors = self.task_planner.validate_plan(execution_plan)
            if not is_valid:
                session.update_state(SessionState.ERROR, {"validation_errors": errors})
                return RouteResult(
                    success=False,
                    mode=AnalysisMode.STATIC,
                    execution_method="direct",
                    error=f"Invalid execution plan: {', '.join(errors)}",
                    error_type="InvalidPlanError",
                    next_state=SessionState.ERROR,
                )

            # 静态分析模式：直接执行
            if self.auto_execute_static:
                # 执行计划
                execution_results = self.execution_engine.execute_plan(execution_plan)
                session.execution_results.extend(execution_results)

                # 生成响应
                response = self._generate_static_response(
                    execution_plan, execution_results
                )
                assistant_message = session.add_message(
                    "assistant", response, {"mode": "static", "auto_executed": True}
                )

                session.update_state(
                    SessionState.ACTIVE,
                    {
                        "execution_completed": True,
                        "results_count": len(execution_results),
                    },
                )

                return RouteResult(
                    success=True,
                    mode=AnalysisMode.STATIC,
                    execution_method="direct",
                    execution_plan=execution_plan,
                    response_message=response,
                    next_state=SessionState.ACTIVE,
                    metadata={
                        "execution_results": len(execution_results),
                        "auto_executed": True,
                    },
                )
            else:
                # 不自动执行，仅创建计划
                response = f"已创建静态分析计划 {execution_plan.plan_id}，包含 {len(execution_plan.tasks)} 个任务。"
                assistant_message = session.add_message(
                    "assistant", response, {"mode": "static", "auto_executed": False}
                )

                session.update_state(
                    SessionState.WAITING_INPUT,
                    {"plan_created": True, "awaiting_execution": True},
                )

                return RouteResult(
                    success=True,
                    mode=AnalysisMode.STATIC,
                    execution_method="manual",
                    execution_plan=execution_plan,
                    response_message=response,
                    next_state=SessionState.WAITING_INPUT,
                )

        except Exception as e:
            session.update_state(SessionState.ERROR, {"routing_error": str(e)})
            return RouteResult(
                success=False,
                mode=AnalysisMode.STATIC,
                execution_method="direct",
                error=str(e),
                error_type=type(e).__name__,
                next_state=SessionState.ERROR,
            )

    def _handle_deep_route(
        self, route_request: RouteRequest, confidence: float
    ) -> RouteResult:
        """处理深度分析路由"""
        session = route_request.session
        user_input = route_request.user_input

        # 更新会话状态
        session.update_state(
            SessionState.PROCESSING, {"routing_mode": "deep", "confidence": confidence}
        )

        # 添加用户消息
        user_message = session.add_message(
            "user", user_input, {"mode": "deep", "routing_confidence": confidence}
        )

        try:
            # 解析用户请求
            current_path = route_request.context.get("current_path", ".")
            user_request = self.task_planner.parse_user_request(
                user_input, current_path
            )
            user_request.mode = AnalysisMode.DEEP  # 确保模式正确

            # 创建执行计划
            execution_plan = self.task_planner.create_execution_plan(user_request)
            session.current_request = user_request
            session.current_plan = execution_plan

            # 验证计划
            is_valid, errors = self.task_planner.validate_plan(execution_plan)
            if not is_valid:
                session.update_state(SessionState.ERROR, {"validation_errors": errors})
                return RouteResult(
                    success=False,
                    mode=AnalysisMode.DEEP,
                    execution_method="interactive",
                    error=f"Invalid execution plan: {', '.join(errors)}",
                    error_type="InvalidPlanError",
                    next_state=SessionState.ERROR,
                )

            # 深度分析模式：启动对话交互
            if self.interactive_deep:
                # 生成交互式响应
                response = f"已创建深度分析计划 {execution_plan.plan_id}。"
                response += f"将使用AI进行智能代码分析，包含 {len(execution_plan.tasks)} 个步骤。\n\n"
                response += "准备开始深度分析，是否继续？"

                assistant_message = session.add_message(
                    "assistant", response, {"mode": "deep", "interactive": True}
                )

                session.update_state(
                    SessionState.WAITING_INPUT,
                    {"deep_analysis_ready": True, "awaiting_confirmation": True},
                )

                return RouteResult(
                    success=True,
                    mode=AnalysisMode.DEEP,
                    execution_method="interactive",
                    execution_plan=execution_plan,
                    response_message=response,
                    next_state=SessionState.WAITING_INPUT,
                    metadata={"interactive": True, "awaiting_confirmation": True},
                )
            else:
                # 直接执行
                execution_results = self.execution_engine.execute_plan(execution_plan)
                session.execution_results.extend(execution_results)

                response = self._generate_deep_response(
                    execution_plan, execution_results
                )
                assistant_message = session.add_message(
                    "assistant", response, {"mode": "deep", "auto_executed": True}
                )

                session.update_state(
                    SessionState.ACTIVE,
                    {
                        "execution_completed": True,
                        "results_count": len(execution_results),
                    },
                )

                return RouteResult(
                    success=True,
                    mode=AnalysisMode.DEEP,
                    execution_method="direct",
                    execution_plan=execution_plan,
                    response_message=response,
                    next_state=SessionState.ACTIVE,
                    metadata={
                        "execution_results": len(execution_results),
                        "auto_executed": True,
                    },
                )

        except Exception as e:
            session.update_state(SessionState.ERROR, {"routing_error": str(e)})
            return RouteResult(
                success=False,
                mode=AnalysisMode.DEEP,
                execution_method="interactive",
                error=str(e),
                error_type=type(e).__name__,
                next_state=SessionState.ERROR,
            )

    def _handle_fix_route(
        self, route_request: RouteRequest, confidence: float
    ) -> RouteResult:
        """处理修复分析路由"""
        session = route_request.session
        user_input = route_request.user_input

        # 更新会话状态
        session.update_state(
            SessionState.PROCESSING, {"routing_mode": "fix", "confidence": confidence}
        )

        # 添加用户消息
        user_message = session.add_message(
            "user", user_input, {"mode": "fix", "routing_confidence": confidence}
        )

        try:
            # 解析用户请求
            current_path = route_request.context.get("current_path", ".")
            user_request = self.task_planner.parse_user_request(
                user_input, current_path
            )
            user_request.mode = AnalysisMode.FIX  # 确保模式正确

            # 创建执行计划
            execution_plan = self.task_planner.create_execution_plan(user_request)
            session.current_request = user_request
            session.current_plan = execution_plan

            # 验证计划
            is_valid, errors = self.task_planner.validate_plan(execution_plan)
            if not is_valid:
                session.update_state(SessionState.ERROR, {"validation_errors": errors})
                return RouteResult(
                    success=False,
                    mode=AnalysisMode.FIX,
                    execution_method="confirmation",
                    error=f"Invalid execution plan: {', '.join(errors)}",
                    error_type="InvalidPlanError",
                    next_state=SessionState.ERROR,
                )

            # 修复模式：包含确认流程
            if self.confirmation_fix:
                # 生成确认响应
                response = f"已创建修复分析计划 {execution_plan.plan_id}。"
                response += f"将检测问题并提供修复建议，包含 {len(execution_plan.tasks)} 个步骤。\n\n"
                response += "⚠️ 修复操作将修改代码文件，建议先查看修复建议。\n"
                response += "是否查看修复建议并继续？"

                assistant_message = session.add_message(
                    "assistant",
                    response,
                    {"mode": "fix", "confirmation_required": True},
                )

                session.update_state(
                    SessionState.WAITING_INPUT,
                    {
                        "fix_analysis_ready": True,
                        "awaiting_confirmation": True,
                        "confirmation_required": True,
                    },
                )

                return RouteResult(
                    success=True,
                    mode=AnalysisMode.FIX,
                    execution_method="confirmation",
                    execution_plan=execution_plan,
                    response_message=response,
                    next_state=SessionState.WAITING_INPUT,
                    metadata={
                        "confirmation_required": True,
                        "awaiting_confirmation": True,
                    },
                )
            else:
                # 直接执行（不推荐）
                execution_results = self.execution_engine.execute_plan(execution_plan)
                session.execution_results.extend(execution_results)

                response = self._generate_fix_response(
                    execution_plan, execution_results
                )
                assistant_message = session.add_message(
                    "assistant", response, {"mode": "fix", "auto_executed": True}
                )

                session.update_state(
                    SessionState.ACTIVE,
                    {
                        "execution_completed": True,
                        "results_count": len(execution_results),
                    },
                )

                return RouteResult(
                    success=True,
                    mode=AnalysisMode.FIX,
                    execution_method="direct",
                    execution_plan=execution_plan,
                    response_message=response,
                    next_state=SessionState.ACTIVE,
                    metadata={
                        "execution_results": len(execution_results),
                        "auto_executed": True,
                        "warning": "Auto-executed fix operations without confirmation",
                    },
                )

        except Exception as e:
            session.update_state(SessionState.ERROR, {"routing_error": str(e)})
            return RouteResult(
                success=False,
                mode=AnalysisMode.FIX,
                execution_method="confirmation",
                error=str(e),
                error_type=type(e).__name__,
                next_state=SessionState.ERROR,
            )

    def _generate_static_response(self, plan: ExecutionPlan, results: List) -> str:
        """生成静态分析响应"""
        success_count = len([r for r in results if r.success])
        total_count = len(results)

        response = f"✅ 静态分析完成！\n\n"
        response += f"📊 执行结果：{success_count}/{total_count} 任务成功\n"
        response += f"📋 分析计划：{plan.plan_id}\n"
        response += f"🎯 目标路径：{plan.target_path}\n\n"

        if success_count < total_count:
            response += "⚠️ 部分任务执行失败，请检查详细日志。\n\n"

        response += "已使用 AST、Pylint、Flake8 和 Bandit 工具完成代码质量检查。"

        return response

    def _generate_deep_response(self, plan: ExecutionPlan, results: List) -> str:
        """生成深度分析响应"""
        success_count = len([r for r in results if r.success])
        total_count = len(results)

        response = f"✨ 深度分析完成！\n\n"
        response += f"🤖 AI分析结果：{success_count}/{total_count} 任务成功\n"
        response += f"📋 分析计划：{plan.plan_id}\n"
        response += f"🎯 目标路径：{plan.target_path}\n\n"

        response += "已使用大语言模型完成智能代码分析，提供了详细的洞察和建议。"

        return response

    def _generate_fix_response(self, plan: ExecutionPlan, results: List) -> str:
        """生成修复响应"""
        success_count = len([r for r in results if r.success])
        total_count = len(results)

        response = f"🔧 修复分析完成！\n\n"
        response += f"🛠️ 修复结果：{success_count}/{total_count} 任务成功\n"
        response += f"📋 修复计划：{plan.plan_id}\n"
        response += f"🎯 目标路径：{plan.target_path}\n\n"

        if success_count > 0:
            response += "✅ 已应用修复建议并更新代码文件。\n"
            response += "💾 已创建备份文件，如需恢复可使用备份管理功能。\n\n"
        else:
            response += "❌ 修复执行失败，请检查详细日志。\n\n"

        response += "已使用智能分析和自动修复功能完成代码问题修复。"

        return response

    def get_supported_modes(self) -> List[str]:
        """获取支持的模式列表"""
        return [mode.value for mode in AnalysisMode]

    def get_mode_description(self, mode: str) -> str:
        """获取模式描述"""
        descriptions = {
            "static": "静态分析：直接使用工具进行代码质量、安全和风格检查",
            "deep": "深度分析：使用AI进行深入的代码分析和建议，支持交互式对话",
            "fix": "修复分析：检测问题并提供修复建议，包含确认流程保护",
        }
        return descriptions.get(mode, "未知模式")
