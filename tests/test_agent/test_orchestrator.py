"""
Agent编排器测试模块
测试会话管理、对话历史和状态转换功能
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from src.agent.orchestrator import (
    AgentOrchestrator, Session, ChatMessage, SessionState, MessageRole
)
from src.agent.planner import UserRequest, ExecutionPlan, AnalysisMode


class TestChatMessage:
    """测试ChatMessage类"""

    def test_chat_message_creation(self):
        """测试聊天消息创建"""
        message = ChatMessage(
            message_id="msg_123",
            role=MessageRole.USER,
            content="Hello, world!"
        )

        assert message.message_id == "msg_123"
        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"
        assert isinstance(message.timestamp, float)
        assert message.metadata == {}

    def test_chat_message_with_metadata(self):
        """测试带元数据的聊天消息"""
        metadata = {"source": "test", "priority": "high"}
        message = ChatMessage(
            message_id="msg_456",
            role=MessageRole.ASSISTANT,
            content="Response message",
            metadata=metadata
        )

        assert message.metadata == metadata

    def test_chat_message_to_dict(self):
        """测试聊天消息转换为字典"""
        message = ChatMessage(
            message_id="msg_789",
            role=MessageRole.SYSTEM,
            content="System notification",
            metadata={"type": "info"}
        )

        result = message.to_dict()
        expected = {
            "message_id": "msg_789",
            "role": "system",
            "content": "System notification",
            "timestamp": message.timestamp,
            "metadata": {"type": "info"}
        }

        assert result == expected


class TestSession:
    """测试Session类"""

    def test_session_creation(self):
        """测试会话创建"""
        session = Session(
            session_id="session_123",
            user_id="user_456"
        )

        assert session.session_id == "session_123"
        assert session.user_id == "user_456"
        assert session.state == SessionState.CREATED
        assert isinstance(session.created_at, float)
        assert isinstance(session.updated_at, float)
        assert len(session.messages) == 0
        assert session.current_request is None
        assert session.current_plan is None
        assert len(session.execution_results) == 0

    def test_session_state_update(self):
        """测试会话状态更新"""
        session = Session(
            session_id="session_789",
            user_id="user_123"
        )

        original_updated_at = session.updated_at
        time.sleep(0.01)  # 确保时间差异

        metadata = {"reason": "user_input"}
        session.update_state(SessionState.ACTIVE, metadata)

        assert session.state == SessionState.ACTIVE
        assert session.updated_at > original_updated_at
        assert session.metadata["reason"] == "user_input"
        assert session.metadata.get("previous_state") == "created"

    def test_add_message(self):
        """测试添加消息"""
        session = Session(
            session_id="session_abc",
            user_id="user_def"
        )

        # 添加用户消息
        user_message = session.add_message(
            MessageRole.USER,
            "Test message",
            {"source": "test"}
        )

        assert len(session.messages) == 1
        assert session.messages[0] == user_message
        assert user_message.role == MessageRole.USER
        assert user_message.content == "Test message"
        assert user_message.metadata["source"] == "test"
        assert user_message.message_id.startswith("msg_")

        # 检查更新时间
        assert session.updated_at > session.created_at

    def test_get_last_user_message(self):
        """测试获取最后一条用户消息"""
        session = Session(
            session_id="session_last",
            user_id="user_last"
        )

        # 没有消息时返回None
        assert session.get_last_user_message() is None

        # 添加助手消息
        session.add_message(MessageRole.ASSISTANT, "Assistant response")
        assert session.get_last_user_message() is None

        # 添加用户消息
        user_msg = session.add_message(MessageRole.USER, "User input")
        assert session.get_last_user_message() == user_msg

        # 添加更多消息
        session.add_message(MessageRole.ASSISTANT, "Another response")
        session.add_message(MessageRole.SYSTEM, "System notification")
        assert session.get_last_user_message() == user_msg

        # 添加新的用户消息
        new_user_msg = session.add_message(MessageRole.USER, "New user input")
        assert session.get_last_user_message() == new_user_msg

    def test_get_conversation_summary(self):
        """测试获取对话摘要"""
        session = Session(
            session_id="session_summary",
            user_id="user_summary"
        )

        # 空会话
        summary = session.get_conversation_summary()
        assert len(summary) == 0

        # 添加消息
        for i in range(15):
            role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
            session.add_message(role, f"Message {i}")

        # 默认获取最近10条
        summary = session.get_conversation_summary()
        assert len(summary) == 10
        assert summary[0].content == "Message 5"
        assert summary[-1].content == "Message 14"

        # 指定数量
        summary = session.get_conversation_summary(max_messages=5)
        assert len(summary) == 5
        assert summary[0].content == "Message 10"
        assert summary[-1].content == "Message 14"

    def test_session_to_dict(self):
        """测试会话转换为字典"""
        session = Session(
            session_id="session_dict",
            user_id="user_dict"
        )

        # 添加一些数据
        session.add_message(MessageRole.USER, "Test message")
        session.update_state(SessionState.ACTIVE, {"test": "data"})

        # 模拟当前请求和计划
        mock_request = Mock()
        mock_request.to_dict.return_value = {"mode": "static"}
        session.current_request = mock_request

        mock_plan = Mock(spec=ExecutionPlan)
        mock_plan.plan_id = "plan_123"
        session.current_plan = mock_plan

        result = session.to_dict()

        assert result["session_id"] == "session_dict"
        assert result["user_id"] == "user_dict"
        assert result["state"] == "active"
        assert result["message_count"] == 1
        assert result["current_request"]["mode"] == "static"
        assert result["current_plan"] == "plan_123"
        assert result["execution_results_count"] == 0
        assert result["metadata"]["test"] == "data"


class TestAgentOrchestrator:
    """测试AgentOrchestrator类"""

    @pytest.fixture
    def mock_config_manager(self):
        """模拟配置管理器"""
        config_manager = Mock()
        config_manager.get_section.return_value = {}
        return config_manager

    @pytest.fixture
    def orchestrator(self, mock_config_manager):
        """创建编排器实例"""
        return AgentOrchestrator(mock_config_manager)

    def test_orchestrator_initialization(self, mock_config_manager):
        """测试编排器初始化"""
        orchestrator = AgentOrchestrator(mock_config_manager)

        assert orchestrator.max_sessions == 1000
        assert orchestrator.session_timeout == 3600
        assert orchestrator.max_messages_per_session == 1000
        assert len(orchestrator.sessions) == 0
        assert len(orchestrator.user_sessions) == 0
        assert orchestrator.task_planner is not None
        assert orchestrator.execution_engine is not None

    def test_create_session(self, orchestrator):
        """测试创建会话"""
        user_id = "test_user"
        metadata = {"source": "unit_test"}

        session = orchestrator.create_session(user_id, metadata)

        assert session.session_id.startswith("session_")
        assert session.user_id == user_id
        assert session.state == SessionState.CREATED
        assert session.metadata["source"] == "unit_test"
        assert session.metadata["created_by"] == "orchestrator"

        # 检查会话是否被存储
        assert session.session_id in orchestrator.sessions
        assert user_id in orchestrator.user_sessions
        assert session.session_id in orchestrator.user_sessions[user_id]

    def test_get_session(self, orchestrator):
        """测试获取会话"""
        # 创建会话
        session = orchestrator.create_session("test_user")

        # 获取存在的会话
        retrieved = orchestrator.get_session(session.session_id)
        assert retrieved == session

        # 获取不存在的会话
        non_existent = orchestrator.get_session("non_existent_session")
        assert non_existent is None

    def test_get_user_sessions(self, orchestrator):
        """测试获取用户会话"""
        user_id = "test_user"

        # 用户没有会话
        sessions = orchestrator.get_user_sessions(user_id)
        assert len(sessions) == 0

        # 创建多个会话
        session1 = orchestrator.create_session(user_id)
        session2 = orchestrator.create_session(user_id)
        other_user_session = orchestrator.create_session("other_user")

        # 获取用户会话
        sessions = orchestrator.get_user_sessions(user_id)
        assert len(sessions) == 2
        assert session1 in sessions
        assert session2 in sessions
        assert other_user_session not in sessions

    def test_process_user_input_success(self, orchestrator):
        """测试成功处理用户输入"""
        # 创建会话
        session = orchestrator.create_session("test_user")

        # 模拟task_planner的parse_user_request和create_execution_plan方法
        mock_request = Mock()
        mock_request.raw_input = "static analysis"
        mock_request.mode = AnalysisMode.STATIC

        mock_plan = Mock()
        mock_plan.plan_id = "plan_123"
        mock_plan.tasks = [Mock() for _ in range(3)]  # 3个任务

        with patch.object(orchestrator.task_planner, 'parse_user_request', return_value=mock_request), \
             patch.object(orchestrator.task_planner, 'create_execution_plan', return_value=mock_plan), \
             patch.object(orchestrator.task_planner, 'validate_plan', return_value=(True, [])), \
             patch.object(orchestrator.execution_engine, 'execute_plan') as mock_execute:

            # 处理用户输入
            user_input = "static analysis of src/"
            result = orchestrator.process_user_input(session.session_id, user_input)

            # 验证结果
            assert result["success"] is True
            assert result["session_id"] == session.session_id
            assert "user_message_id" in result
            assert "assistant_message_id" in result
            assert result["execution_plan"] == "plan_123"
            assert result["task_count"] == 3
            assert "estimated_duration" in result
            assert "response" in result

            # 验证会话状态
            assert session.state == SessionState.ACTIVE
            assert session.current_request == mock_request
            assert session.current_plan == mock_plan
            assert len(session.messages) == 2  # 用户消息 + 助手响应

            # 验证调用
            orchestrator.task_planner.parse_user_request.assert_called_once_with(user_input, '.')
            orchestrator.task_planner.create_execution_plan.assert_called_once_with(mock_request)
            orchestrator.task_planner.validate_plan.assert_called_once_with(mock_plan)
            orchestrator.execution_engine.execute_plan.assert_called_once_with(mock_plan)

    def test_process_user_input_session_not_found(self, orchestrator):
        """测试处理不存在会话的用户输入"""
        result = orchestrator.process_user_input("non_existent", "test input")

        assert result["success"] is False
        assert result["error"] == "Session non_existent not found"
        assert result["error_type"] == "SessionNotFoundError"

    def test_process_user_input_invalid_state(self, orchestrator):
        """测试在无效状态下处理用户输入"""
        session = orchestrator.create_session("test_user")

        # 设置为无效状态
        session.update_state(SessionState.COMPLETED)

        result = orchestrator.process_user_input(session.session_id, "test input")

        assert result["success"] is False
        assert "Cannot process input" in result["error"]
        assert result["error_type"] == "InvalidStateError"

    def test_process_user_input_plan_validation_failure(self, orchestrator):
        """测试执行计划验证失败"""
        session = orchestrator.create_session("test_user")

        mock_request = Mock()
        mock_plan = Mock()

        with patch.object(orchestrator.task_planner, 'parse_user_request', return_value=mock_request), \
             patch.object(orchestrator.task_planner, 'create_execution_plan', return_value=mock_plan), \
             patch.object(orchestrator.task_planner, 'validate_plan', return_value=(False, ["Error 1", "Error 2"])):

            result = orchestrator.process_user_input(session.session_id, "test input")

            assert result["success"] is False
            assert "Invalid execution plan" in result["error"]
            assert result["error_type"] == "InvalidPlanError"
            assert "validation_errors" in result
            assert len(result["validation_errors"]) == 2

            # 验证会话状态
            assert session.state == SessionState.ERROR

    def test_get_session_history(self, orchestrator):
        """测试获取会话历史"""
        session = orchestrator.create_session("test_user")

        # 添加消息
        session.add_message(MessageRole.USER, "User message 1")
        session.add_message(MessageRole.ASSISTANT, "Assistant response 1")
        session.add_message(MessageRole.SYSTEM, "System message")
        session.add_message(MessageRole.USER, "User message 2")

        # 获取所有历史（包含系统消息）
        history = orchestrator.get_session_history(session.session_id, include_system_messages=True)
        assert len(history) == 4

        # 获取历史（不包含系统消息）
        history = orchestrator.get_session_history(session.session_id, include_system_messages=False)
        assert len(history) == 3
        assert all(msg.role != MessageRole.SYSTEM for msg in history)

        # 限制数量
        history = orchestrator.get_session_history(session.session_id, limit=2)
        assert len(history) == 2

    def test_transition_session_state(self, orchestrator):
        """测试会话状态转换"""
        session = orchestrator.create_session("test_user")

        # 有效转换
        success = orchestrator.transition_session_state(
            session.session_id,
            SessionState.ACTIVE,
            "user_input"
        )
        assert success is True
        assert session.state == SessionState.ACTIVE
        assert session.metadata["state_transition_reason"] == "user_input"

        # 无效转换
        success = orchestrator.transition_session_state(
            session.session_id,
            SessionState.CREATED,  # 不能从ACTIVE回到CREATED
            "invalid"
        )
        assert success is False
        assert session.state == SessionState.ACTIVE  # 状态未改变

        # 不存在的会话
        success = orchestrator.transition_session_state(
            "non_existent",
            SessionState.COMPLETED
        )
        assert success is False

    def test_close_session(self, orchestrator):
        """测试关闭会话"""
        session = orchestrator.create_session("test_user")

        # 关闭会话
        success = orchestrator.close_session(session.session_id, "test_close")

        assert success is True
        assert session.state == SessionState.COMPLETED
        assert session.metadata["close_reason"] == "test_close"
        assert session.metadata["closed_at"] > 0

        # 会话不再在用户会话列表中
        user_sessions = orchestrator.get_user_sessions("test_user")
        assert session not in user_sessions

        # 关闭不存在的会话
        success = orchestrator.close_session("non_existent")
        assert success is False

    def test_get_session_statistics_single_session(self, orchestrator):
        """测试获取单个会话统计"""
        session = orchestrator.create_session("test_user")

        # 添加一些数据
        session.add_message(MessageRole.USER, "User message")
        session.add_message(MessageRole.ASSISTANT, "Assistant response")
        session.update_state(SessionState.ACTIVE)

        stats = orchestrator.get_session_statistics(session_id=session.session_id)

        assert stats["session_id"] == session.session_id
        assert stats["user_id"] == "test_user"
        assert stats["state"] == "active"
        assert stats["message_count"] == 2
        assert stats["user_message_count"] == 1
        assert stats["assistant_message_count"] == 1
        assert "duration" in stats
        assert stats["has_active_plan"] is False
        assert stats["execution_results_count"] == 0

    def test_get_session_statistics_user(self, orchestrator):
        """测试获取用户统计"""
        user_id = "test_user"

        # 创建多个会话
        session1 = orchestrator.create_session(user_id)
        session2 = orchestrator.create_session(user_id)
        session3 = orchestrator.create_session(user_id)

        # 设置不同状态
        session1.update_state(SessionState.ACTIVE)
        session2.update_state(SessionState.PROCESSING)
        session3.update_state(SessionState.COMPLETED)

        # 添加消息
        session1.add_message(MessageRole.USER, "Message")
        session2.add_message(MessageRole.USER, "Message")
        session2.add_message(MessageRole.ASSISTANT, "Response")

        stats = orchestrator.get_session_statistics(user_id=user_id)

        assert stats["user_id"] == user_id
        assert stats["total_sessions"] == 3
        assert stats["active_sessions"] == 2  # ACTIVE + PROCESSING
        assert stats["total_messages"] == 3
        assert stats["average_messages_per_session"] == 1.0
        assert "sessions_by_state" in stats
        assert stats["sessions_by_state"]["active"] == 1
        assert stats["sessions_by_state"]["processing"] == 1
        assert stats["sessions_by_state"]["completed"] == 1

    def test_get_session_statistics_global(self, orchestrator):
        """测试获取全局统计"""
        # 创建多个用户的会话
        orchestrator.create_session("user1")
        orchestrator.create_session("user2")
        user3_session = orchestrator.create_session("user3")

        user3_session.add_message(MessageRole.USER, "Test")

        stats = orchestrator.get_session_statistics()

        assert stats["total_sessions"] == 3
        assert stats["total_users"] == 3
        assert stats["total_messages"] == 1
        assert "sessions_by_state" in stats
        assert "average_session_duration" in stats

    def test_can_process_input(self, orchestrator):
        """测试检查是否可以处理输入"""
        # 这些状态应该可以处理输入
        processable_states = [
            SessionState.CREATED,
            SessionState.ACTIVE,
            SessionState.WAITING_INPUT
        ]

        for state in processable_states:
            assert orchestrator._can_process_input(state) is True

        # 这些状态不应该可以处理输入
        non_processable_states = [
            SessionState.PROCESSING,
            SessionState.SUSPENDED,
            SessionState.COMPLETED,
            SessionState.ERROR
        ]

        for state in non_processable_states:
            assert orchestrator._can_process_input(state) is False

    def test_generate_assistant_response(self, orchestrator):
        """测试生成助手响应"""
        session = orchestrator.create_session("test_user")

        # 测试静态分析响应
        static_plan = Mock()
        static_plan.mode = AnalysisMode.STATIC
        static_plan.plan_id = "plan_static"
        static_plan.tasks = [Mock() for _ in range(4)]

        response = orchestrator._generate_assistant_response(session, static_plan)
        assert "静态分析计划" in response
        assert "plan_static" in response
        assert "4 个任务" in response

        # 测试深度分析响应
        deep_plan = Mock()
        deep_plan.mode = AnalysisMode.DEEP
        deep_plan.plan_id = "plan_deep"
        deep_plan.tasks = [Mock() for _ in range(3)]

        response = orchestrator._generate_assistant_response(session, deep_plan)
        assert "深度分析计划" in response
        assert "plan_deep" in response

        # 测试修复分析响应
        fix_plan = Mock()
        fix_plan.mode = AnalysisMode.FIX
        fix_plan.plan_id = "plan_fix"
        fix_plan.tasks = [Mock() for _ in range(6)]

        response = orchestrator._generate_assistant_response(session, fix_plan)
        assert "修复分析计划" in response
        assert "plan_fix" in response

    def test_estimate_plan_duration(self, orchestrator):
        """测试估算计划执行时间"""
        # 创建包含不同任务类型的计划
        plan = Mock()
        plan.tasks = [
            Mock(task_type="file_selection"),
            Mock(task_type="ast_analysis"),
            Mock(task_type="pylint_analysis"),
            Mock(task_type="report_generation")
        ]

        duration = orchestrator._estimate_plan_duration(plan)

        # 基础时间 + file_selection(1.0) + ast_analysis(2.0) + pylint_analysis(5.0) + report_generation(1.0)
        assert duration == 2.0 + 1.0 + 2.0 + 5.0 + 1.0

    def test_is_session_expired(self, orchestrator):
        """测试检查会话是否过期"""
        session = Session(
            session_id="test_session",
            user_id="test_user"
        )

        # 新会话不应该过期
        assert orchestrator._is_session_expired(session) is False

        # 模拟过期会话
        session.updated_at = time.time() - orchestrator.session_timeout - 1
        assert orchestrator._is_session_expired(session) is True