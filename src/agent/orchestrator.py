"""
Agent编排器模块
负责协调和管理用户会话、对话历史和状态转换
"""

import uuid
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ..utils.logger import get_logger
from ..utils.config import get_config_manager
from .planner import TaskPlanner, UserRequest, ExecutionPlan
from .execution_engine import ExecutionEngine, ExecutionResult


class SessionState(Enum):
    """会话状态枚举"""
    CREATED = "created"
    ACTIVE = "active"
    WAITING_INPUT = "waiting_input"
    PROCESSING = "processing"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    ERROR = "error"


class MessageRole(Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ChatMessage:
    """聊天消息数据结构"""
    message_id: str
    role: MessageRole
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "message_id": self.message_id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


@dataclass
class Session:
    """用户会话数据结构"""
    session_id: str
    user_id: str
    state: SessionState = SessionState.CREATED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    messages: List[ChatMessage] = field(default_factory=list)
    current_request: Optional[UserRequest] = None
    current_plan: Optional[ExecutionPlan] = None
    execution_results: List[ExecutionResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_state(self, new_state: SessionState, metadata: Optional[Dict[str, Any]] = None):
        """更新会话状态"""
        old_state = self.state
        self.state = new_state
        self.updated_at = time.time()

        # 添加状态转换信息
        state_info = {
            "previous_state": old_state.value,
            "state_transition_time": self.updated_at
        }

        if metadata:
            self.metadata.update(metadata)
            self.metadata.update(state_info)
        else:
            self.metadata.update(state_info)

    def add_message(self, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None):
        """添加消息到会话"""
        message = ChatMessage(
            message_id=f"msg_{uuid.uuid4().hex[:8]}",
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.updated_at = time.time()
        return message

    def get_last_user_message(self) -> Optional[ChatMessage]:
        """获取最后一条用户消息"""
        for message in reversed(self.messages):
            if message.role == MessageRole.USER:
                return message
        return None

    def get_conversation_summary(self, max_messages: int = 10) -> List[ChatMessage]:
        """获取对话摘要（最近N条消息）"""
        return self.messages[-max_messages:] if self.messages else []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": len(self.messages),
            "current_request": self.current_request.to_dict() if self.current_request else None,
            "current_plan": self.current_plan.plan_id if self.current_plan else None,
            "execution_results_count": len(self.execution_results),
            "metadata": self.metadata
        }


class AgentOrchestrator:
    """Agent编排器主类"""

    def __init__(self, config_manager=None):
        """
        初始化Agent编排器

        Args:
            config_manager: 配置管理器实例
        """
        self.logger = get_logger()
        self.config_manager = config_manager or get_config_manager()

        # 获取配置
        try:
            self.config = self.config_manager.get_section('orchestrator') or {}
        except:
            self.config = {}

        # 会话管理配置
        self.max_sessions = self.config.get('max_sessions', 1000)
        self.session_timeout = self.config.get('session_timeout', 3600)  # 1小时
        self.max_messages_per_session = self.config.get('max_messages_per_session', 1000)

        # 初始化组件
        self.task_planner = TaskPlanner(config_manager)
        self.execution_engine = ExecutionEngine(config_manager)

        # 会话存储
        self.sessions: Dict[str, Session] = {}
        self.user_sessions: Dict[str, List[str]] = {}  # user_id -> [session_ids]

        # 状态转换规则
        self.state_transitions = self._init_state_transitions()

        # 会话清理任务
        self.last_cleanup_time = time.time()
        self.cleanup_interval = self.config.get('cleanup_interval', 300)  # 5分钟

        self.logger.info("AgentOrchestrator initialized")

    def create_session(self, user_id: str, initial_metadata: Optional[Dict[str, Any]] = None) -> Session:
        """
        创建新的用户会话

        Args:
            user_id: 用户ID
            initial_metadata: 初始元数据

        Returns:
            新创建的会话对象
        """
        # 检查会话数量限制
        self._cleanup_expired_sessions()
        if len(self.sessions) >= self.max_sessions:
            self._remove_oldest_sessions()

        # 创建会话
        session = Session(
            session_id=f"session_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            metadata=initial_metadata or {}
        )

        # 添加到存储
        self.sessions[session.session_id] = session
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = []
        self.user_sessions[user_id].append(session.session_id)

        # 更新状态
        session.update_state(SessionState.CREATED, {"created_by": "orchestrator"})

        self.logger.info(f"Created session {session.session_id} for user {user_id}")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        获取会话

        Args:
            session_id: 会话ID

        Returns:
            会话对象或None
        """
        return self.sessions.get(session_id)

    def get_user_sessions(self, user_id: str, include_expired: bool = False) -> List[Session]:
        """
        获取用户的所有会话

        Args:
            user_id: 用户ID
            include_expired: 是否包含过期会话

        Returns:
            会话列表
        """
        if user_id not in self.user_sessions:
            return []

        sessions = []
        for session_id in self.user_sessions[user_id]:
            session = self.sessions.get(session_id)
            if session:
                if include_expired or not self._is_session_expired(session):
                    sessions.append(session)

        return sessions

    def process_user_input(self, session_id: str, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理用户输入

        Args:
            session_id: 会话ID
            user_input: 用户输入
            context: 上下文信息

        Returns:
            处理结果
        """
        session = self.get_session(session_id)
        if not session:
            return {
                "success": False,
                "error": f"Session {session_id} not found",
                "error_type": "SessionNotFoundError"
            }

        try:
            # 检查会话状态
            if not self._can_process_input(session.state):
                return {
                    "success": False,
                    "error": f"Cannot process input in state {session.state.value}",
                    "error_type": "InvalidStateError"
                }

            # 检查消息数量限制
            if len(session.messages) >= self.max_messages_per_session:
                return {
                    "success": False,
                    "error": "Session message limit exceeded",
                    "error_type": "MessageLimitExceededError"
                }

            # 更新会话状态
            session.update_state(SessionState.PROCESSING, {"processing_input": user_input})

            # 添加用户消息
            user_message = session.add_message(
                MessageRole.USER,
                user_input,
                context or {}
            )

            # 解析用户请求
            current_path = context.get('current_path', '.') if context else '.'
            user_request = self.task_planner.parse_user_request(user_input, current_path)
            session.current_request = user_request

            # 创建执行计划
            execution_plan = self.task_planner.create_execution_plan(user_request)
            session.current_plan = execution_plan

            # 验证执行计划
            is_valid, errors = self.task_planner.validate_plan(execution_plan)
            if not is_valid:
                session.update_state(SessionState.ERROR, {"validation_errors": errors})
                return {
                    "success": False,
                    "error": f"Invalid execution plan: {', '.join(errors)}",
                    "error_type": "InvalidPlanError",
                    "validation_errors": errors
                }

            # 执行计划（异步执行任务）
            self.execution_engine.execute_plan(execution_plan)

            # 更新会话状态
            session.update_state(SessionState.ACTIVE, {
                "last_user_input": user_input,
                "plan_id": execution_plan.plan_id,
                "task_count": len(execution_plan.tasks)
            })

            # 生成助手响应
            assistant_response = self._generate_assistant_response(session, execution_plan)
            assistant_message = session.add_message(
                MessageRole.ASSISTANT,
                assistant_response,
                {"response_type": "plan_created", "plan_id": execution_plan.plan_id}
            )

            self.logger.info(f"Processed user input for session {session_id}, created plan {execution_plan.plan_id}")

            return {
                "success": True,
                "session_id": session_id,
                "user_message_id": user_message.message_id,
                "assistant_message_id": assistant_message.message_id,
                "execution_plan": execution_plan.plan_id,
                "task_count": len(execution_plan.tasks),
                "estimated_duration": self._estimate_plan_duration(execution_plan),
                "response": assistant_response
            }

        except Exception as e:
            session.update_state(SessionState.ERROR, {"error": str(e), "error_type": type(e).__name__})
            self.logger.error(f"Failed to process user input for session {session_id}: {e}")

            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "session_id": session_id
            }

    def get_session_history(self, session_id: str, include_system_messages: bool = False, limit: Optional[int] = None) -> List[ChatMessage]:
        """
        获取会话历史

        Args:
            session_id: 会话ID
            include_system_messages: 是否包含系统消息
            limit: 消息数量限制

        Returns:
            消息列表
        """
        session = self.get_session(session_id)
        if not session:
            return []

        messages = session.messages

        # 过滤系统消息
        if not include_system_messages:
            messages = [msg for msg in messages if msg.role != MessageRole.SYSTEM]

        # 限制数量
        if limit and limit > 0:
            messages = messages[-limit:]

        return messages

    def transition_session_state(self, session_id: str, new_state: SessionState, reason: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        转换会话状态

        Args:
            session_id: 会话ID
            new_state: 新状态
            reason: 转换原因
            metadata: 额外元数据

        Returns:
            转换是否成功
        """
        session = self.get_session(session_id)
        if not session:
            self.logger.error(f"Session {session_id} not found for state transition")
            return False

        current_state = session.state

        # 检查状态转换是否有效
        if new_state not in self.state_transitions.get(current_state, []):
            self.logger.warning(f"Invalid state transition: {current_state.value} -> {new_state.value}")
            return False

        # 执行转换
        old_state = session.state
        session.update_state(new_state, {
            "state_transition_reason": reason,
            "previous_state": old_state.value,
            **(metadata or {})
        })

        self.logger.info(f"Session {session_id} state transition: {old_state.value} -> {new_state.value}" + (f" ({reason})" if reason else ""))
        return True

    def close_session(self, session_id: str, reason: Optional[str] = None) -> bool:
        """
        关闭会话

        Args:
            session_id: 会话ID
            reason: 关闭原因

        Returns:
            关闭是否成功
        """
        session = self.get_session(session_id)
        if not session:
            return False

        # 更新状态为已完成
        session.update_state(SessionState.COMPLETED, {
            "close_reason": reason or "user_initiated",
            "closed_at": time.time()
        })

        # 从活跃会话列表中移除
        if session.user_id in self.user_sessions:
            if session_id in self.user_sessions[session.user_id]:
                self.user_sessions[session.user_id].remove(session_id)

        self.logger.info(f"Closed session {session_id}" + (f" ({reason})" if reason else ""))
        return True

    def get_session_statistics(self, session_id: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取会话统计信息

        Args:
            session_id: 特定会话ID（可选）
            user_id: 特定用户ID（可选）

        Returns:
            统计信息
        """
        if session_id:
            # 单个会话统计
            session = self.get_session(session_id)
            if not session:
                return {}

            return {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "state": session.state.value,
                "message_count": len(session.messages),
                "user_message_count": len([m for m in session.messages if m.role == MessageRole.USER]),
                "assistant_message_count": len([m for m in session.messages if m.role == MessageRole.ASSISTANT]),
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "duration": session.updated_at - session.created_at,
                "has_active_plan": session.current_plan is not None,
                "execution_results_count": len(session.execution_results)
            }

        elif user_id:
            # 用户会话统计
            user_sessions = self.get_user_sessions(user_id)

            total_messages = sum(len(s.messages) for s in user_sessions)
            active_sessions = len([s for s in user_sessions if s.state in [SessionState.ACTIVE, SessionState.PROCESSING]])

            return {
                "user_id": user_id,
                "total_sessions": len(user_sessions),
                "active_sessions": active_sessions,
                "total_messages": total_messages,
                "average_messages_per_session": total_messages / len(user_sessions) if user_sessions else 0,
                "sessions_by_state": self._count_sessions_by_state(user_sessions)
            }

        else:
            # 全局统计
            all_sessions = list(self.sessions.values())
            total_users = len(self.user_sessions)

            return {
                "total_sessions": len(all_sessions),
                "total_users": total_users,
                "active_sessions": len([s for s in all_sessions if s.state in [SessionState.ACTIVE, SessionState.PROCESSING]]),
                "total_messages": sum(len(s.messages) for s in all_sessions),
                "sessions_by_state": self._count_sessions_by_state(all_sessions),
                "average_session_duration": self._calculate_average_session_duration(all_sessions)
            }

    def _init_state_transitions(self) -> Dict[SessionState, List[SessionState]]:
        """初始化状态转换规则"""
        return {
            SessionState.CREATED: [SessionState.ACTIVE, SessionState.ERROR],
            SessionState.ACTIVE: [SessionState.WAITING_INPUT, SessionState.PROCESSING, SessionState.SUSPENDED, SessionState.COMPLETED, SessionState.ERROR],
            SessionState.WAITING_INPUT: [SessionState.ACTIVE, SessionState.PROCESSING, SessionState.SUSPENDED, SessionState.COMPLETED, SessionState.ERROR],
            SessionState.PROCESSING: [SessionState.ACTIVE, SessionState.WAITING_INPUT, SessionState.SUSPENDED, SessionState.COMPLETED, SessionState.ERROR],
            SessionState.SUSPENDED: [SessionState.ACTIVE, SessionState.COMPLETED, SessionState.ERROR],
            SessionState.COMPLETED: [],  # 终态
            SessionState.ERROR: [SessionState.ACTIVE, SessionState.SUSPENDED, SessionState.COMPLETED]  # 错误恢复
        }

    def _can_process_input(self, state: SessionState) -> bool:
        """检查当前状态是否可以处理用户输入"""
        return state in [SessionState.ACTIVE, SessionState.WAITING_INPUT, SessionState.CREATED]

    def _is_session_expired(self, session: Session) -> bool:
        """检查会话是否过期"""
        return (time.time() - session.updated_at) > self.session_timeout

    def _cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = time.time()
        if current_time - self.last_cleanup_time < self.cleanup_interval:
            return

        expired_sessions = []
        for session_id, session in self.sessions.items():
            if self._is_session_expired(session) and session.state != SessionState.COMPLETED:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            self.close_session(session_id, "session_expired")

        if expired_sessions:
            self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

        self.last_cleanup_time = current_time

    def _remove_oldest_sessions(self, count: int = 10):
        """移除最旧的会话以释放空间"""
        # 按更新时间排序，移除最旧的会话
        sorted_sessions = sorted(
            self.sessions.items(),
            key=lambda x: x[1].updated_at
        )

        removed_count = 0
        for session_id, session in sorted_sessions:
            if session.state == SessionState.COMPLETED:
                if self.close_session(session_id, "session_cleanup"):
                    del self.sessions[session_id]
                    removed_count += 1
                    if removed_count >= count:
                        break

        if removed_count > 0:
            self.logger.info(f"Removed {removed_count} oldest sessions for cleanup")

    def _generate_assistant_response(self, session: Session, plan: ExecutionPlan) -> str:
        """生成助手响应"""
        if plan.mode.value == "static":
            return f"已创建静态分析计划 {plan.plan_id}，包含 {len(plan.tasks)} 个任务。将使用AST、Pylint、Flake8和Bandit工具进行代码质量检查。"
        elif plan.mode.value == "deep":
            return f"已创建深度分析计划 {plan.plan_id}，包含 {len(plan.tasks)} 个任务。将使用LLM进行智能代码分析。"
        elif plan.mode.value == "fix":
            return f"已创建修复分析计划 {plan.plan_id}，包含 {len(plan.tasks)} 个任务。将检测问题并提供修复建议。"
        else:
            return f"已创建分析计划 {plan.plan_id}，包含 {len(plan.tasks)} 个任务。"

    def _estimate_plan_duration(self, plan: ExecutionPlan) -> float:
        """估算计划执行时间"""
        # 基于任务类型和数量的简单估算
        base_time = 2.0  # 基础时间（秒）
        task_time = {
            "file_selection": 1.0,
            "ast_analysis": 2.0,
            "pylint_analysis": 5.0,
            "flake8_analysis": 3.0,
            "bandit_analysis": 4.0,
            "llm_analysis": 10.0,
            "report_generation": 1.0
        }

        total_time = base_time
        for task in plan.tasks:
            total_time += task_time.get(task.task_type, 2.0)

        return total_time

    def _count_sessions_by_state(self, sessions: List[Session]) -> Dict[str, int]:
        """按状态统计会话数量"""
        state_counts = {}
        for session in sessions:
            state = session.state.value
            state_counts[state] = state_counts.get(state, 0) + 1
        return state_counts

    def _calculate_average_session_duration(self, sessions: List[Session]) -> float:
        """计算平均会话持续时间"""
        if not sessions:
            return 0.0

        total_duration = sum(s.updated_at - s.created_at for s in sessions)
        return total_duration / len(sessions)