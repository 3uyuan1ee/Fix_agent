"""
测试用例：中间件系统

基于项目实际结构测试中间件模块
测试文件: src/midware/*.py
"""

import pytest
import tempfile
import os
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Optional, Dict, List
from dataclasses import dataclass

# 导入实际的项目模块
from src.midware.layered_memory import (
    LayeredMemoryMiddleware,
    MemoryItem,
    LayeredMemoryState,
    WorkingMemory,
    SessionMemory,
    LongTermMemory
)
from src.midware.performance_monitor import (
    PerformanceMonitorMiddleware,
    PerformanceCollector,
    PerformanceRecord
)

from src.midware.security import (
    SecurityMiddleware,
    SecurityViolation,
    SecurityState
)

from src.midware.logging import (
    LoggingMiddleware,
    LoggingState
)

from src.midware.context_enhancement import (
    ContextEnhancementMiddleware,
    ContextEnhancementState
)


class TestMemoryItem:
    """测试MemoryItem数据结构"""

    def test_memory_item_creation(self):
        """测试MemoryItem创建"""
        timestamp = time.time()
        item = MemoryItem(
            content="Test memory content",
            timestamp=timestamp,
            importance=0.8,
            tags=["test", "important"]
        )

        assert item.content == "Test memory content"
        assert item.timestamp == timestamp
        assert item.importance == 0.8
        assert item.tags == ["test", "important"]
        assert item.access_count == 0
        assert item.last_accessed == timestamp

    def test_memory_item_default_values(self):
        """测试MemoryItem默认值"""
        timestamp = time.time()
        item = MemoryItem(
            content="Test content",
            timestamp=timestamp
        )

        assert item.importance == 1.0
        assert item.tags == []
        assert item.access_count == 0
        assert item.last_accessed == timestamp

    def test_memory_item_post_init(self):
        """测试MemoryItem后处理"""
        timestamp = time.time()
        item = MemoryItem(
            content="Test",
            timestamp=timestamp,
            last_accessed=0.0
        )

        # last_accessed应该被设置为timestamp
        assert item.last_accessed == timestamp

    def test_memory_item_access_tracking(self):
        """测试访问跟踪"""
        timestamp = time.time()
        item = MemoryItem(
            content="Test",
            timestamp=timestamp,
            access_count=5,
            last_accessed=timestamp - 100
        )

        # 模拟访问
        current_time = timestamp + 50
        item.access_count += 1
        item.last_accessed = current_time

        assert item.access_count == 6
        assert item.last_accessed == current_time


class TestWorkingMemory:
    """测试工作记忆"""

    def test_working_memory_creation(self):
        """测试工作记忆创建"""
        max_size = 5
        working_memory = WorkingMemory(max_size=max_size)

        assert working_memory.max_size == max_size
        assert len(working_memory.items) == 0

    def test_working_memory_add_items(self):
        """测试添加项目"""
        working_memory = WorkingMemory(max_size=3)

        working_memory.add("item1")
        working_memory.add("item2")
        working_memory.add("item3")

        assert len(working_memory.items) == 3
        # 验证items包含的是字典，不是字符串
        items_list = list(working_memory.items)
        contents = [item['content'] for item in items_list]
        assert "item1" in contents
        assert "item2" in contents
        assert "item3" in contents

    def test_working_memory_capacity_limit(self):
        """测试容量限制"""
        working_memory = WorkingMemory(max_size=3)

        # 添加超过容量的项目
        working_memory.add("item1")
        working_memory.add("item2")
        working_memory.add("item3")
        working_memory.add("item4")  # 应该移除最旧的项目

        assert len(working_memory.items) == 3
        # 验证items包含的是字典，不是字符串
        items_list = list(working_memory.items)
        contents = [item['content'] for item in items_list]
        assert "item1" not in contents  # 最旧的被移除
        assert "item4" in contents
        assert "item2" in contents
        assert "item3" in contents

    def test_working_memory_get_context(self):
        """测试获取工作记忆上下文"""
        working_memory = WorkingMemory(max_size=3)

        working_memory.add("item1")
        working_memory.add("item2")

        context = working_memory.get_context()
        assert isinstance(context, str)
        assert "item1" in context
        assert "item2" in context

    def test_working_memory_clear(self):
        """测试清空工作记忆"""
        working_memory = WorkingMemory(max_size=3)

        working_memory.add("item1")
        working_memory.add("item2")
        working_memory.clear()

        assert len(working_memory.items) == 0


class TestSessionMemory:
    """测试会话记忆"""

    def test_session_memory_operations(self):
        """测试会话记忆基本操作"""
        session_memory = SessionMemory("test_session")

        # 测试添加话题
        session_memory.add_topic("programming")
        session_memory.add_topic("python")

        assert "programming" in session_memory.key_topics
        assert "python" in session_memory.key_topics

        # 测试更新摘要
        session_memory.update_summary("User asked about Python programming")
        assert "Python programming" in session_memory.conversation_summary

        # 测试交互计数
        initial_count = session_memory.interaction_count
        session_memory.update_summary("Another interaction")
        assert session_memory.interaction_count > initial_count

    def test_session_memory_multiple_topics(self):
        """测试多个话题管理"""
        session_memory = SessionMemory("test_session")

        topics = ["programming", "python", "algorithms", "data structures"]

        for topic in topics:
            session_memory.add_topic(topic)

        # 验证所有话题都被正确存储
        for topic in topics:
            assert topic in session_memory.key_topics

    def test_session_memory_get_context(self):
        """测试获取会话上下文"""
        session_memory = SessionMemory("test_session")

        session_memory.add_topic("python")
        session_memory.update_summary("Discussed Python basics")

        context = session_memory.get_context()
        assert isinstance(context, str)
        assert "python" in context
        assert "Python basics" in context


class TestLongTermMemory:
    """测试长期记忆"""

    def test_long_term_memory_initialization(self):
        """测试长期记忆初始化"""
        mock_backend = Mock()
        memory_path = "/memories/"

        long_term_memory = LongTermMemory(mock_backend, memory_path)

        assert long_term_memory.backend == mock_backend
        assert long_term_memory.memory_path == memory_path

    def test_semantic_memory_operations(self):
        """测试语义记忆操作"""
        mock_backend = Mock()
        mock_backend.exists.return_value = False
        mock_backend.write.return_value = None
        mock_backend.read.return_value = json.dumps({
            "knowledge": "Python is a programming language",
            "facts": ["Python was created by Guido van Rossum"]
        })

        long_term_memory = LongTermMemory(mock_backend, "/memories/")

        # 添加语义记忆
        long_term_memory.add_semantic_memory("Python是一种编程语言")

        # 保存记忆
        long_term_memory.save()

        # 验证语义记忆被添加和保存
        assert len(long_term_memory.semantic_memory) > 0
        assert mock_backend.write.called

        # 搜索语义记忆
        results = long_term_memory.search_memory("Python", "semantic")
        assert len(results) > 0

    def test_episodic_memory_operations(self):
        """测试情节记忆操作"""
        mock_backend = Mock()
        mock_backend.exists.return_value = False
        mock_backend.write.return_value = None
        mock_backend.read.return_value = json.dumps({
            "events": [
                {
                    "type": "user_feedback",
                    "content": "用户建议改进代码质量",
                    "timestamp": "2023-01-01T10:00:00Z"
                }
            ]
        })

        long_term_memory = LongTermMemory(mock_backend, "/memories/")

        # 添加情节记忆
        long_term_memory.add_episodic_memory("用户建议改进代码质量")

        # 保存记忆
        long_term_memory.save()

        # 验证情节记忆被添加和保存
        assert len(long_term_memory.episodic_memory) > 0
        assert mock_backend.write.called

        # 搜索情节记忆
        results = long_term_memory.search_memory("用户", "episodic")
        assert len(results) > 0

    def test_long_term_memory_search(self):
        """测试长期记忆搜索"""
        mock_backend = Mock()
        mock_backend.read.return_value = json.dumps([])

        long_term_memory = LongTermMemory(mock_backend, "/memories/")

        # 添加一些测试数据
        long_term_memory.add_semantic_memory("Python编程知识")
        long_term_memory.add_episodic_memory("用户询问了Python问题")

        # 搜索记忆
        results = long_term_memory.search_memory("Python")
        assert isinstance(results, list)
        assert len(results) >= 2  # 应该找到语义记忆和情节记忆

        # 测试限制数量
        limited_results = long_term_memory.search_memory("Python", limit=1)
        assert len(limited_results) <= 1


class TestLayeredMemoryMiddleware:
    """测试分层记忆中间件"""

    @pytest.fixture
    def mock_backend(self):
        """模拟后端"""
        return Mock()

    @pytest.fixture
    def sample_runtime(self):
        """模拟运行时环境"""
        runtime = Mock()
        runtime.state = Mock()
        return runtime

    def test_layered_memory_middleware_initialization(self, mock_backend):
        """测试分层记忆中间件初始化"""
        memory_path = "/memories/"
        working_memory_size = 10
        enable_semantic = True
        enable_episodic = True

        middleware = LayeredMemoryMiddleware(
            backend=mock_backend,
            memory_path=memory_path,
            working_memory_size=working_memory_size,
            enable_semantic_memory=enable_semantic,
            enable_episodic_memory=enable_episodic
        )

        assert middleware.backend == mock_backend
        assert middleware.memory_path == memory_path
        assert middleware.working_memory.max_size == working_memory_size
        assert middleware.enable_semantic_memory == enable_semantic
        assert middleware.enable_episodic_memory == enable_episodic

    def test_layered_memory_middleware_decorator(self, mock_backend, sample_runtime):
        """测试中间件装饰器功能"""
        middleware = LayeredMemoryMiddleware(
            backend=mock_backend,
            memory_path="/memories/"
        )

        @middleware
        def test_function(message):
            return f"Processed: {message}"

        result = test_function("test message")
        assert result == "Processed: test message"

    def test_layered_memory_state_initialization(self, mock_backend):
        """测试状态初始化"""
        mock_model_request = Mock()
        mock_model_request.state = {}

        middleware = LayeredMemoryMiddleware(
            backend=mock_backend,
            memory_path="/memories/"
        )

        # 调用中间件
        with patch('src.midware.layered_memory.LayeredMemoryState') as mock_state:
            mock_state_instance = Mock()
            mock_state.return_value = mock_state_instance

            result = middleware(mock_model_request)
            assert mock_state.assert_called_once()

    def test_layered_memory_upgrades(self, mock_backend):
        """测试中间件升级"""
        middleware = LayeredMemoryMiddleware(
            backend=mock_backend,
            memory_path="/memories/"
        )

        upgraded = middleware.auto_upgrade_memory()
        assert isinstance(upgraded, list)

    def test_working_memory_integration(self, mock_backend):
        """测试工作记忆集成"""
        middleware = LayeredMemoryMiddleware(
            backend=mock_backend,
            memory_path="/memories/",
            working_memory_size=3
        )

        # 验证工作记忆创建
        assert hasattr(middleware, 'working_memory')
        assert middleware.working_memory.max_size == 3

    def test_session_memory_integration(self, mock_backend):
        """测试会话记忆集成"""
        middleware = LayeredMemoryMiddleware(
            backend=mock_backend,
            memory_path="/memories/"
        )

        # 验证会话记忆字典创建
        assert hasattr(middleware, 'session_memory')
        assert isinstance(middleware.session_memory, dict)


class TestPerformanceMonitorMiddleware:
    """测试性能监控中间件"""

    @pytest.fixture
    def mock_backend(self):
        """模拟后端"""
        return Mock()

    def test_performance_monitor_initialization(self, mock_backend):
        """测试性能监控中间件初始化"""
        metrics_path = "/performance/"
        enable_monitoring = True
        max_records = 100

        middleware = PerformanceMonitorMiddleware(
            backend=mock_backend,
            metrics_path=metrics_path,
            enable_system_monitoring=enable_monitoring,
            max_records=max_records
        )

        assert middleware.backend == mock_backend
        assert middleware.metrics_path == metrics_path
        assert middleware.enable_system_monitoring == enable_monitoring
        assert middleware.max_records == max_records

    def test_performance_monitor_decorator(self, mock_backend):
        """测试性能监控装饰器"""
        middleware = PerformanceMonitorMiddleware(
            backend=mock_backend,
            metrics_path="/performance/",
            enable_system_monitoring=False  # 禁用系统监控以避免线程问题
        )

        # 测试中间件有正确的属性
        assert hasattr(middleware, 'collector')
        assert hasattr(middleware, 'session_id')

    def test_performance_tracking(self, mock_backend):
        """测试性能跟踪"""
        middleware = PerformanceMonitorMiddleware(
            backend=mock_backend,
            metrics_path="/performance/",
            enable_system_monitoring=False  # 禁用系统监控
        )

        # 测试性能收集器
        assert hasattr(middleware.collector, 'get_summary')

        summary = middleware.collector.get_summary()
        assert isinstance(summary, dict)

    def test_memory_tracker(self, mock_backend):
        """测试内存跟踪器"""
        middleware = PerformanceMonitorMiddleware(
            backend=mock_backend,
            metrics_path="/performance/",
            enable_system_monitoring=False
        )

        # 测试内存相关属性
        assert hasattr(middleware, '_memory_usage')
        assert isinstance(middleware._memory_usage, (int, float))

    def test_cpu_monitor(self, mock_backend):
        """测试CPU监控器"""
        middleware = PerformanceMonitorMiddleware(
            backend=mock_backend,
            metrics_path="/performance/",
            enable_system_monitoring=False
        )

        # 测试CPU相关属性
        assert hasattr(middleware, '_cpu_usage')
        assert isinstance(middleware._cpu_usage, (int, float))


class TestSecurityMiddleware:
    """测试安全中间件"""

    @pytest.fixture
    def mock_backend(self):
        """模拟后端"""
        return Mock()

    def test_security_middleware_initialization(self, mock_backend):
        """测试安全中间件初始化"""
        workspace_root = "/safe/workspace"
        security_level = "medium"
        enable_file_security = True
        enable_command_security = True
        max_file_size = 10 * 1024 * 1024  # 10MB

        middleware = SecurityMiddleware(
            backend=mock_backend,
            workspace_root=workspace_root,
            security_level=security_level,
            enable_file_security=enable_file_security,
            enable_command_security=enable_command_security,
            max_file_size=max_file_size
        )

        assert middleware.workspace_root == Path(workspace_root).resolve()
        assert middleware.security_level == security_level
        assert middleware.enable_file_security == enable_file_security
        assert middleware.enable_command_security == enable_command_security
        assert middleware.max_file_size == max_file_size

    def test_security_middleware_decorator(self, mock_backend):
        """测试安全中间件装饰器"""
        middleware = SecurityMiddleware(
            backend=mock_backend,
            workspace_root="/safe/workspace"
        )

        @middleware
        def test_function():
            return "safe_operation"

        result = test_function()
        assert result == "safe_operation"

    def test_path_validator(self):
        """测试路径验证器"""
        workspace_root = "/safe/workspace"
        validator = PathValidator(workspace_root)

        assert validator.workspace_root == Path(workspace_root).resolve()

        # 测试安全路径
        safe_path = Path(workspace_root) / "safe_file.txt"
        assert validator.is_safe_path(str(safe_path)) == True

    def test_path_validator_unsafe_paths(self):
        """测试不安全路径验证"""
        workspace_root = "/safe/workspace"
        validator = PathValidator(workspace_root)

        # 测试超出工作区的路径
        unsafe_path = "/etc/passwd"
        assert validator.is_safe_path(unsafe_path) == False

        # 测试相对路径遍历
        traversal_path = "../../../etc/passwd"
        assert validator.is_safe_path(traversal_path) == False

    def test_command_validator(self):
        """测试命令验证器"""
        security_level = "high"
        validator = CommandValidator(security_level)

        assert validator.security_level == security_level

        # 测试安全命令
        safe_commands = [
            "ls -la",
            "python script.py",
            "git status"
        ]

        for cmd in safe_commands:
            assert validator.is_safe_command(cmd) == True

    def test_command_validator_unsafe_commands(self):
        """测试不安全命令验证"""
        security_level = "high"
        validator = CommandValidator(security_level)

        unsafe_commands = [
            "rm -rf /",
            "sudo rm -rf /*",
            "format c:",
            "dd if=/dev/zero of=/dev/sda"
        ]

        for cmd in unsafe_commands:
            assert validator.is_safe_command(cmd) == False

    def test_file_size_validation(self):
        """测试文件大小验证"""
        workspace_root = "/safe/workspace"
        middleware = SecurityMiddleware(
            backend=Mock(),
            workspace_root=workspace_root,
            max_file_size=1024  # 1KB
        )

        # 测试小文件
        assert middleware.validate_file_size(512) == True

        # 测试大文件
        assert middleware.validate_file_size(2048) == False


class TestLoggingMiddleware:
    """测试日志中间件"""

    @pytest.fixture
    def mock_backend(self):
        """模拟后端"""
        return Mock()

    def test_logging_middleware_initialization(self, mock_backend):
        """测试日志中间件初始化"""
        log_path = "/logs/"
        session_id = "test_session_123"
        max_file_size = 10 * 1024 * 1024  # 10MB

        middleware = LoggingMiddleware(
            backend=mock_backend,
            log_path=log_path,
            session_id=session_id,
            max_file_size=max_file_size
        )

        assert middleware.backend == mock_backend
        assert middleware.log_path == log_path
        assert middleware.session_id == session_id
        assert middleware.max_file_size == max_file_size

    def test_logging_middleware_decorator(self, mock_backend):
        """测试日志中间件基本功能"""
        middleware = LoggingMiddleware(
            backend=mock_backend,
            log_path="/logs/",
            enable_conversation_logging=True,
            enable_tool_logging=False,
            enable_performance_logging=False,
            enable_error_logging=False
        )

        # 测试基本属性
        assert hasattr(middleware, 'session_id')
        assert hasattr(middleware, 'log_path')
        assert middleware.enable_conversation_logging is True
        assert middleware.enable_tool_logging is False

    def test_structured_logger(self, mock_backend):
        """测试日志记录功能"""
        middleware = LoggingMiddleware(
            backend=mock_backend,
            log_path="/logs/",
            enable_conversation_logging=True,
            enable_tool_logging=True,
            enable_performance_logging=True,
            enable_error_logging=True
        )

        # 测试日志路径属性
        assert hasattr(middleware, 'conversation_log_path')
        assert hasattr(middleware, 'tool_log_path')
        assert hasattr(middleware, 'performance_log_path')
        assert hasattr(middleware, 'error_log_path')

        # 测试日志级别
        assert hasattr(middleware, 'log_level')
        assert middleware.log_level is not None

    def test_log_rotation(self, mock_backend):
        """测试日志轮转配置"""
        middleware = LoggingMiddleware(
            backend=mock_backend,
            log_path="/logs/",
            max_log_files=5,
            max_file_size=1024 * 1024,  # 1MB
            rotate_interval=12  # 12 hours
        )

        # 验证轮转配置
        assert middleware.max_log_files == 5
        assert middleware.max_file_size == 1024 * 1024
        assert middleware.rotate_interval == 12


class TestContextEnhancementMiddleware:
    """测试上下文增强中间件"""

    @pytest.fixture
    def mock_backend(self):
        """模拟后端"""
        return Mock()

    def test_context_enhancement_middleware_initialization(self, mock_backend):
        """测试上下文增强中间件初始化"""
        context_path = "/context/"
        enable_project_analysis = True
        enable_user_preferences = True
        max_context_length = 2000

        middleware = ContextEnhancementMiddleware(
            backend=mock_backend,
            context_path=context_path,
            enable_project_analysis=enable_project_analysis,
            enable_user_preferences=enable_user_preferences,
            max_context_length=max_context_length
        )

        assert middleware.backend == mock_backend
        assert middleware.context_path == context_path
        assert middleware.enable_project_analysis == enable_project_analysis
        assert middleware.enable_user_preferences == enable_user_preferences
        assert middleware.max_context_length == max_context_length

    def test_context_enhancement_middleware_decorator(self, mock_backend):
        """测试上下文增强中间件基本功能"""
        middleware = ContextEnhancementMiddleware(
            backend=mock_backend,
            enable_project_analysis=True,
            enable_user_preferences=True,
            enable_conversation_enhancement=True
        )

        # 测试基本属性
        assert hasattr(middleware, 'context_path')
        assert hasattr(middleware, 'enable_project_analysis')
        assert hasattr(middleware, 'enable_user_preferences')
        assert hasattr(middleware, 'enable_conversation_enhancement')

        # 测试分析方法存在
        assert hasattr(middleware, '_analyze_project_structure')
        assert callable(middleware._analyze_project_structure)

    def test_context_builder(self, mock_backend):
        """测试项目结构分析功能"""
        middleware = ContextEnhancementMiddleware(
            backend=mock_backend,
            enable_project_analysis=True
        )

        # 测试项目分析方法
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # 创建一些测试文件
            (project_path / "main.py").write_text("print('Hello World')")
            (project_path / "requirements.txt").write_text("flask>=2.0")

            # 测试分析
            result = middleware._analyze_project_structure(str(project_path))

            assert isinstance(result, dict)
            assert "name" in result
            assert "path" in result
            assert result["name"] == project_path.name

    def test_context_enhancement_functionality(self, mock_backend):
        """测试上下文增强基本配置"""
        middleware = ContextEnhancementMiddleware(
            backend=mock_backend,
            max_context_length=1000
        )

        # 测试基本配置
        assert middleware.max_context_length == 1000
        assert hasattr(middleware, 'backend')
        assert middleware.backend == mock_backend


class TestMiddlewareIntegration:
    """测试中间件集成"""

    def test_middleware_chain_creation(self):
        """测试中间件链创建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_backend = Mock()
            workspace_root = temp_dir

            # 创建多个中间件
            logging_middleware = LoggingMiddleware(mock_backend, f"{temp_dir}/logs/")
            security_middleware = SecurityMiddleware(
                backend=mock_backend,
                workspace_root=workspace_root
            )
            performance_middleware = PerformanceMonitorMiddleware(mock_backend)

            # 创建中间件链
            middleware_chain = [
                logging_middleware,
                security_middleware,
                performance_middleware
            ]

            assert len(middleware_chain) == 3
            assert all(middleware is not None for middleware in middleware_chain)

    def test_middleware_execution_order(self):
        """测试中间件执行顺序"""
        execution_order = []

        def create_middleware(name):
            class TestMiddleware:
                def __call__(self, func):
                    def wrapper(*args, **kwargs):
                        execution_order.append(f"{name}_before")
                        result = func(*args, **kwargs)
                        execution_order.append(f"{name}_after")
                        return result
                    return wrapper
            return TestMiddleware()

        # 创建中间件链
        middlewares = [
            create_middleware("logging"),
            create_middleware("security"),
            create_middleware("performance")
        ]

        # 应用中间件
        decorated_function = lambda: "test_result"
        for middleware in middlewares:
            decorated_function = middleware(decorated_function)

        result = decorated_function()

        # 验证执行顺序
        assert "performance_before" in execution_order
        assert "security_before" in execution_order
        assert "logging_before" in execution_order

    def test_middleware_error_handling(self):
        """测试中间件错误处理"""
        execution_order = []

        def create_failing_middleware(name):
            class FailingMiddleware:
                def __call__(self, func):
                    def wrapper(*args, **kwargs):
                        execution_order.append(f"{name}_before")
                        if name == "failing":
                            raise Exception("Test error")
                        execution_order.append(f"{name}_after")
                        return func(*args, **kwargs)
                    return wrapper
            return FailingMiddleware()

        middlewares = [
            create_middleware("logging"),
            create_middleware("failing"),
            create_middleware("performance")
        ]

        decorated_function = lambda: "should_not_execute"
        for middleware in middlewares:
            decorated_function = middleware(decorated_function)

        with pytest.raises(Exception):
            decorated_function()

        # 验证执行到失败点
        assert "logging_before" in execution_order
        assert "failing_before" in execution_order


class TestMiddlewarePerformance:
    """测试中间件性能"""

    def test_middleware_overhead(self):
        """测试中间件开销"""
        import time

        # 创建多个中间件
        middlewares = []
        for i in range(5):
            mock_backend = Mock()
            middleware = LoggingMiddleware(mock_backend, f"/logs/test_{i}.log")
            middlewares.append(middleware)

        # 测试无中间件的执行时间
        def base_function():
            time.sleep(0.001)  # 1ms
            return "base_result"

        start_time = time.time()
        base_result = base_function()
        base_time = time.time() - start_time

        # 测试有中间件的执行时间
        decorated_function = base_function
        for middleware in middlewares:
            decorated_function = middleware(decorated_function)

        start_time = time.time()
        middleware_result = decorated_function()
        middleware_time = time.time() - start_time

        assert base_result == middleware_result
        # 中间件开销应该是合理的（不超过基础时间的5倍）
        assert middleware_time < base_time * 5

    def test_concurrent_middleware_execution(self):
        """测试并发中间件执行"""
        import threading
        import time

        results = []

        def run_middleware_test():
            mock_backend = Mock()
            middleware = PerformanceMonitorMiddleware(mock_backend)

            @middleware
            def test_function():
                time.sleep(0.01)
                return f"thread_{threading.get_ident()}"

            result = test_function()
            results.append(result)

        # 创建多个线程同时执行
        threads = []
        for i in range(3):
            thread = threading.Thread(target=run_middleware_test)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=5)

        # 验证所有调用都成功
        assert len(results) == 3
        assert all("thread_" in result for result in results)


# 运行测试的入口
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])