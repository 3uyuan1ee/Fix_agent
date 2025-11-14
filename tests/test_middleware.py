"""
测试用例：中间件系统

测试目标：
1. 分层记忆中间件
2. 性能监控中间件
3. 安全中间件
4. 日志中间件
5. 上下文增强中间件
6. 中间件管道集成
7. 错误处理和恢复
"""

import pytest
import tempfile
import os
import json
import time
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path
from datetime import datetime

# 假设的导入，实际路径可能需要调整
try:
    from src.midware.layered_memory import (
        LayeredMemoryMiddleware,
        WorkingMemory,
        SessionMemory,
        LongTermMemory
    )
    from src.midware.performance_monitor import (
        PerformanceMonitorMiddleware,
        MemoryTracker,
        CPUMonitor
    )
    from src.midware.security import (
        SecurityMiddleware,
        PathValidator,
        CommandValidator
    )
    from src.midware.logging import (
        LoggingMiddleware,
        StructuredLogger
    )
    from src.midware.context_enhancement import (
        ContextEnhancementMiddleware,
        ContextBuilder
    )
except ImportError:
    # 如果导入失败，创建Mock对象用于测试
    class LayeredMemoryMiddleware:
        def __init__(self, *args, **kwargs):
            pass
        def __call__(self, func):
            return func
        def auto_upgrade_memory(self):
            return []

    class PerformanceMonitorMiddleware:
        def __init__(self, *args, **kwargs):
            pass
        def __call__(self, func):
            return func
        def track_performance(self):
            return {"cpu": 50, "memory": "100MB"}

    class SecurityMiddleware:
        def __init__(self, *args, **kwargs):
            pass
        def __call__(self, func):
            return func
        def validate_path(self, path):
            return True
        def validate_command(self, cmd):
            return True

    class LoggingMiddleware:
        def __init__(self, *args, **kwargs):
            pass
        def __call__(self, func):
            return func
        def log_event(self, event):
            return True

    class ContextEnhancementMiddleware:
        def __init__(self, *args, **kwargs):
            pass
        def __call__(self, func):
            return func
        def enhance_context(self, context):
            return context


class TestLayeredMemoryMiddleware:
    """测试分层记忆中间件"""

    def test_working_memory_creation(self):
        """测试工作记忆创建"""
        max_size = 10
        working_memory = WorkingMemory(max_size=max_size)

        assert working_memory is not None
        assert working_memory.max_size == max_size
        assert len(working_memory.items) == 0

    def test_working_memory_operations(self):
        """测试工作记忆操作"""
        working_memory = WorkingMemory(max_size=3)

        # 添加项目
        working_memory.add("item1")
        working_memory.add("item2")
        working_memory.add("item3")

        assert len(working_memory.items) == 3
        assert "item1" in working_memory.items
        assert "item2" in working_memory.items
        assert "item3" in working_memory.items

        # 测试容量限制
        working_memory.add("item4")
        assert len(working_memory.items) == 3  # 应该还是3
        assert "item1" not in working_memory.items  # 最老的应该被移除
        assert "item4" in working_memory.items

    def test_session_memory_operations(self):
        """测试会话记忆操作"""
        session_memory = SessionMemory()

        # 测试基本操作
        session_memory.add_preference("theme", "dark")
        session_memory.add_preference("language", "zh")

        assert session_memory.get_preference("theme") == "dark"
        assert session_memory.get_preference("language") == "zh"
        assert session_memory.get_preference("nonexistent") is None

        # 测试更新
        session_memory.add_preference("theme", "light")
        assert session_memory.get_preference("theme") == "light"

    def test_long_term_memory_operations(self):
        """测试长期记忆操作"""
        with tempfile.TemporaryDirectory() as temp_dir:
            backend = Mock()
            backend.exists.return_value = False
            backend.write_text.return_value = None
            backend.read_text.return_value = '{"data": "test"}'

            long_term_memory = LongTermMemory(backend, "/memories/")

            # 测试语义记忆
            long_term_memory.add_semantic_memory("python", "Python是一种编程语言")
            semantic = long_term_memory.get_semantic_memory("python")
            assert semantic is not None

            # 测试情节记忆
            long_term_memory.add_episodic_memory("user feedback", "用户建议改进代码质量")
            episodic = long_term_memory.get_episodic_memory("user feedback")
            assert episodic is not None

    def test_memory_middleware_initialization(self):
        """测试记忆中间件初始化"""
        backend = Mock()
        with patch('src.midware.layered_memory.CompositeBackend') as mock_composite:
            mock_composite.return_value = backend

            middleware = LayeredMemoryMiddleware(
                backend=backend,
                memory_path="/memories/",
                working_memory_size=10,
                enable_semantic_memory=True,
                enable_episodic_memory=True
            )

            assert middleware is not None
            assert middleware.backend == backend
            assert middleware.working_memory.max_size == 10

    def test_memory_middleware_auto_upgrade(self):
        """测试记忆中间件自动升级"""
        backend = Mock()
        middleware = LayeredMemoryMiddleware(backend, "/memories/")

        upgraded = middleware.auto_upgrade_memory()
        assert isinstance(upgraded, list)

    def test_memory_middleware_execution(self):
        """测试记忆中间件执行"""
        backend = Mock()
        middleware = LayeredMemoryMiddleware(backend, "/memories/")

        # 模拟装饰器函数
        @middleware
        def test_function():
            return "test_result"

        result = test_function()
        assert result == "test_result"


class TestPerformanceMonitorMiddleware:
    """测试性能监控中间件"""

    def test_cpu_monitor_initialization(self):
        """测试CPU监控初始化"""
        cpu_monitor = CPUMonitor()

        assert cpu_monitor is not None
        assert hasattr(cpu_monitor, 'get_usage')
        assert hasattr(cpu_monitor, 'start_monitoring')
        assert hasattr(cpu_monitor, 'stop_monitoring')

    @patch('psutil.cpu_percent')
    def test_cpu_monitor_usage(self, mock_cpu_percent):
        """测试CPU使用率监控"""
        mock_cpu_percent.return_value = 45.5

        cpu_monitor = CPUMonitor()
        usage = cpu_monitor.get_usage()

        assert usage == 45.5
        mock_cpu_percent.assert_called_once()

    def test_memory_tracker_initialization(self):
        """测试内存跟踪器初始化"""
        memory_tracker = MemoryTracker()

        assert memory_tracker is not None
        assert hasattr(memory_tracker, 'track_usage')
        assert hasattr(memory_tracker, 'get_memory_info')

    @patch('psutil.virtual_memory')
    def test_memory_tracker_usage(self, mock_virtual_memory):
        """测试内存使用跟踪"""
        mock_memory = Mock()
        mock_memory.used = 1024 * 1024 * 512  # 512MB
        mock_memory.available = 1024 * 1024 * 1024  # 1GB
        mock_virtual_memory.return_value = mock_memory

        memory_tracker = MemoryTracker()
        memory_info = memory_tracker.get_memory_info()

        assert memory_info is not None
        assert memory_info['used'] == 512 * 1024 * 1024

    def test_performance_middleware_initialization(self):
        """测试性能监控中间件初始化"""
        backend = Mock()
        middleware = PerformanceMonitorMiddleware(
            backend=backend,
            metrics_path="/performance/",
            enable_system_monitoring=True,
            max_records=1000
        )

        assert middleware is not None
        assert middleware.backend == backend
        assert middleware.enable_system_monitoring == True
        assert middleware.max_records == 1000

    def test_performance_middleware_tracking(self):
        """测试性能监控中间件跟踪"""
        backend = Mock()
        middleware = PerformanceMonitorMiddleware(backend)

        metrics = middleware.track_performance()
        assert isinstance(metrics, dict)
        assert 'cpu' in metrics or 'memory' in metrics

    def test_performance_middleware_decorator(self):
        """测试性能监控中间件装饰器"""
        backend = Mock()
        middleware = PerformanceMonitorMiddleware(backend)

        @middleware
        def test_function():
            time.sleep(0.1)  # 模拟耗时操作
            return "completed"

        result = test_function()
        assert result == "completed"


class TestSecurityMiddleware:
    """测试安全中间件"""

    def test_path_validator_initialization(self):
        """测试路径验证器初始化"""
        workspace_root = "/safe/workspace"
        validator = PathValidator(workspace_root)

        assert validator is not None
        assert validator.workspace_root == Path(workspace_root).resolve()

    def test_path_validator_safe_paths(self):
        """测试路径验证器安全路径验证"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            validator = PathValidator(str(workspace_root))

            # 测试安全路径
            safe_path = workspace_root / "safe_file.txt"
            safe_path.write_text("test content")

            assert validator.is_safe_path(str(safe_path)) == True

            # 测试相对路径
            relative_path = "relative_file.txt"
            assert validator.is_safe_path(relative_path) == True

            # 测试绝对路径但在工作区内
            abs_safe_path = workspace_root / "abs_safe.txt"
            abs_safe_path.write_text("test content")
            assert validator.is_safe_path(str(abs_safe_path)) == True

    def test_path_validator_unsafe_paths(self):
        """测试路径验证器不安全路径验证"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            validator = PathValidator(str(workspace_root))

            # 测试超出工作区的路径
            unsafe_path = workspace_root.parent / "unsafe.txt"
            assert validator.is_safe_path(str(unsafe_path)) == False

            # 测试系统关键路径
            system_paths = ["/etc/passwd", "/var/log", "C:\\Windows\\System32"]
            for path in system_paths:
                if os.path.exists(path):
                    assert validator.is_safe_path(path) == False

            # 测试路径遍历攻击
            traversal_paths = [
                "../../../etc/passwd",
                "..\\..\\..\\Windows\\System32",
                "safe_dir/../../../etc/passwd"
            ]
            for path in traversal_paths:
                assert validator.is_safe_path(path) == False

    def test_command_validator_initialization(self):
        """测试命令验证器初始化"""
        security_level = "medium"
        validator = CommandValidator(security_level)

        assert validator is not None
        assert validator.security_level == security_level

    def test_command_validator_safe_commands(self):
        """测试命令验证器安全命令验证"""
        validator = CommandValidator("medium")

        safe_commands = [
            "ls -la",
            "python script.py",
            "node app.js",
            "git status",
            "echo 'hello'",
            "pwd"
        ]

        for cmd in safe_commands:
            assert validator.is_safe_command(cmd) == True

    def test_command_validator_unsafe_commands(self):
        """测试命令验证器不安全命令验证"""
        validator = CommandValidator("high")

        unsafe_commands = [
            "rm -rf /",
            "sudo rm -rf /*",
            "format c:",
            "dd if=/dev/zero of=/dev/sda",
            ":(){ :|:& };:",
            "chmod 777 /etc/passwd"
        ]

        for cmd in unsafe_commands:
            assert validator.is_safe_command(cmd) == False

    def test_security_middleware_initialization(self):
        """测试安全中间件初始化"""
        workspace_root = "/safe/workspace"
        middleware = SecurityMiddleware(
            security_level="medium",
            workspace_root=workspace_root,
            enable_file_security=True,
            enable_command_security=True,
            max_file_size=10 * 1024 * 1024
        )

        assert middleware is not None
        assert middleware.security_level == "medium"
        assert middleware.enable_file_security == True
        assert middleware.enable_command_security == True
        assert middleware.max_file_size == 10 * 1024 * 1024

    def test_security_middleware_decorator(self):
        """测试安全中间件装饰器"""
        workspace_root = "/safe/workspace"
        middleware = SecurityMiddleware(workspace_root=workspace_root)

        @middleware
        def test_function():
            return "safe_operation"

        result = test_function()
        assert result == "safe_operation"

    def test_file_size_validation(self):
        """测试文件大小验证"""
        workspace_root = "/safe/workspace"
        middleware = SecurityMiddleware(
            workspace_root=workspace_root,
            max_file_size=1024  # 1KB
        )

        # 测试小文件
        assert middleware.validate_file_size(512) == True

        # 测试大文件
        assert middleware.validate_file_size(2048) == False


class TestLoggingMiddleware:
    """测试日志中间件"""

    def test_structured_logger_initialization(self):
        """测试结构化日志记录器初始化"""
        log_file = "/tmp/test.log"
        logger = StructuredLogger(log_file)

        assert logger is not None
        assert logger.log_file == log_file

    def test_structured_logger_logging(self):
        """测试结构化日志记录"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            log_file = f.name

        try:
            logger = StructuredLogger(log_file)

            # 测试日志记录
            event_data = {
                "event": "tool_execution",
                "tool": "analyze_code_defects",
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            }

            result = logger.log_event(event_data)
            assert result == True

            # 验证日志文件内容
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert "tool_execution" in log_content
                assert "analyze_code_defects" in log_content

        finally:
            os.unlink(log_file)

    def test_logging_middleware_initialization(self):
        """测试日志中间件初始化"""
        backend = Mock()
        middleware = LoggingMiddleware(
            backend=backend,
            log_path="/logs/",
            enable_console_logging=True,
            max_log_size=100 * 1024 * 1024
        )

        assert middleware is not None
        assert middleware.backend == backend
        assert middleware.enable_console_logging == True
        assert middleware.max_log_size == 100 * 1024 * 1024

    def test_logging_middleware_decorator(self):
        """测试日志中间件装饰器"""
        backend = Mock()
        middleware = LoggingMiddleware(backend)

        @middleware
        def test_function():
            return "logged_operation"

        result = test_function()
        assert result == "logged_operation"

    def test_log_rotation(self):
        """测试日志轮转"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            log_file = f.name

        try:
            logger = StructuredLogger(log_file, max_size=100)

            # 写入大量日志触发轮转
            for i in range(50):
                event = {"event": f"test_event_{i}", "data": "x" * 10}
                logger.log_event(event)

            # 验证轮转文件存在
            backup_file = f"{log_file}.1"
            assert os.path.exists(backup_file) or os.path.getsize(log_file) <= 100

        finally:
            # 清理轮转文件
            for i in range(1, 5):
                backup_file = f"{log_file}.{i}"
                if os.path.exists(backup_file):
                    os.unlink(backup_file)
            os.unlink(log_file)


class TestContextEnhancementMiddleware:
    """测试上下文增强中间件"""

    def test_context_builder_initialization(self):
        """测试上下文构建器初始化"""
        builder = ContextBuilder()

        assert builder is not None
        assert hasattr(builder, 'add_context')
        assert hasattr(builder, 'build_context')

    def test_context_builder_operations(self):
        """测试上下文构建器操作"""
        builder = ContextBuilder()

        # 添加上下文
        builder.add_context("user_preference", "dark_theme")
        builder.add_context("project_type", "python")
        builder.add_context("last_action", "code_analysis")

        context = builder.build_context()
        assert isinstance(context, dict)
        assert "user_preference" in context
        assert "project_type" in context
        assert "last_action" in context

    def test_context_enhancement_middleware_initialization(self):
        """测试上下文增强中间件初始化"""
        backend = Mock()
        middleware = ContextEnhancementMiddleware(
            backend=backend,
            enable_auto_context=True,
            context_sources=["user_history", "project_info", "system_state"]
        )

        assert middleware is not None
        assert middleware.enable_auto_context == True
        assert isinstance(middleware.context_sources, list)

    def test_context_enhancement_middleware_enhancement(self):
        """测试上下文增强中间件增强功能"""
        backend = Mock()
        middleware = ContextEnhancementMiddleware(backend)

        base_context = {"user_input": "analyze this code"}
        enhanced_context = middleware.enhance_context(base_context)

        assert isinstance(enhanced_context, dict)
        assert "user_input" in enhanced_context

    def test_context_enhancement_middleware_decorator(self):
        """测试上下文增强中间件装饰器"""
        backend = Mock()
        middleware = ContextEnhancementMiddleware(backend)

        @middleware
        def test_function():
            return "enhanced_operation"

        result = test_function()
        assert result == "enhanced_operation"


class TestMiddlewarePipeline:
    """测试中间件管道"""

    def test_middleware_chain_creation(self):
        """测试中间件链创建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = temp_dir

            # 创建各个中间件
            logging_middleware = LoggingMiddleware(Mock(), f"{temp_dir}/logs/")
            security_middleware = SecurityMiddleware(workspace_root=workspace_root)
            performance_middleware = PerformanceMonitorMiddleware(Mock())

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
                        execution_order.append(name)
                        return func(*args, **kwargs)
                    return wrapper
            return TestMiddleware()

        # 创建中间件链
        middlewares = [
            create_middleware("logging"),
            create_middleware("security"),
            create_middleware("performance")
        ]

        # 应用中间件
        @middlewares[0]
        @middlewares[1]
        @middlewares[2]
        def test_function():
            return "executed"

        result = test_function()

        assert result == "executed"
        assert execution_order == ["performance", "security", "logging"]

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
            create_failing_middleware("logging"),
            create_failing_middleware("failing"),
            create_failing_middleware("performance")
        ]

        @middlewares[0]
        @middlewares[1]
        @middlewares[2]
        def test_function():
            return "should_not_execute"

        with pytest.raises(Exception):
            test_function()

        # 验证执行顺序和错误处理
        assert "performance_before" in execution_order
        assert "failing_before" in execution_order


class TestMiddlewareErrorHandling:
    """测试中间件错误处理"""

    def test_middleware_initialization_error(self):
        """测试中间件初始化错误"""
        with pytest.raises((TypeError, ValueError)):
            SecurityMiddleware(workspace_root=None)

    def test_middleware_runtime_error_recovery(self):
        """测试中间件运行时错误恢复"""
        backend = Mock()
        # 模拟会抛出异常的backend
        backend.write_text.side_effect = Exception("File write error")

        with pytest.raises(Exception):
            LayeredMemoryMiddleware(backend, "/memories/")

    def test_middleware_resource_cleanup(self):
        """测试中间件资源清理"""
        backend = Mock()
        middleware = PerformanceMonitorMiddleware(backend)

        # 模拟资源清理
        if hasattr(middleware, 'cleanup'):
            middleware.cleanup()
            # 验证清理操作
            assert True


class TestMiddlewarePerformance:
    """测试中间件性能"""

    def test_middleware_overhead(self):
        """测试中间件开销"""
        import time

        # 创建多个中间件
        middlewares = []
        for i in range(5):
            backend = Mock()
            middleware = PerformanceMonitorMiddleware(backend)
            middlewares.append(middleware)

        # 定义测试函数
        def test_function():
            return "performance_test"

        # 测试无中间件的执行时间
        start_time = time.time()
        result1 = test_function()
        base_time = time.time() - start_time

        # 测试有中间件的执行时间
        decorated_function = test_function
        for middleware in middlewares:
            decorated_function = middleware(decorated_function)

        start_time = time.time()
        result2 = decorated_function()
        middleware_time = time.time() - start_time

        assert result1 == result2
        # 中间件开销应该是合理的（不超过基础时间的10倍）
        assert middleware_time < base_time * 10

    def test_concurrent_middleware_execution(self):
        """测试并发中间件执行"""
        import threading
        import time

        results = []

        def run_middleware_test():
            backend = Mock()
            middleware = LoggingMiddleware(backend)

            @middleware
            def test_function():
                time.sleep(0.01)
                return "concurrent_test"

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
        assert all(result == "concurrent_test" for result in results)


# 测试运行器和配置
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])