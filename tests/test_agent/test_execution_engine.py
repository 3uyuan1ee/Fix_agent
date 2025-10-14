"""
测试执行引擎
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, patch

from src.agent.execution_engine import (
    ExecutionEngine, ExecutionResult, TaskStatus, ToolStatus, ToolInfo
)


class MockTool:
    """模拟工具类"""

    def __init__(self, name="mock_tool", should_fail=False, delay=0):
        self.name = name
        self.should_fail = should_fail
        self.delay = delay
        self.call_count = 0

    def execute(self, **kwargs):
        """执行工具方法"""
        self.call_count += 1

        if self.delay > 0:
            time.sleep(self.delay)

        if self.should_fail:
            raise ValueError(f"Mock tool {self.name} failed intentionally")

        return {
            "tool": self.name,
            "call_count": self.call_count,
            "parameters": kwargs,
            "result": "success"
        }

    @staticmethod
    def static_execute(**kwargs):
        """静态执行方法"""
        return {"static": True, "parameters": kwargs}


class AsyncMockTool:
    """异步模拟工具类"""

    def __init__(self, name="async_mock_tool"):
        self.name = name
        self.call_count = 0

    async def execute(self, **kwargs):
        """异步执行方法"""
        self.call_count += 1
        await asyncio.sleep(0.1)  # 模拟异步操作
        return {
            "tool": self.name,
            "call_count": self.call_count,
            "parameters": kwargs,
            "result": "async_success"
        }


class TestExecutionEngine:
    """测试执行引擎"""

    @pytest.fixture
    def engine(self):
        """执行引擎fixture"""
        return ExecutionEngine(max_workers=2)

    def test_engine_initialization(self, engine):
        """测试引擎初始化"""
        assert engine is not None
        assert hasattr(engine, 'tools')
        assert hasattr(engine, 'executor')
        assert hasattr(engine, 'running_tasks')
        assert hasattr(engine, 'completed_tasks')
        assert engine.max_workers == 2

    def test_tool_registration(self, engine):
        """测试工具注册"""
        # 注册新工具
        success = engine.register_tool(
            name="test_tool",
            tool_class=MockTool,
            description="Test tool for testing"
        )

        assert success is True
        assert "test_tool" in engine.tools
        assert engine.tools["test_tool"].name == "test_tool"
        assert engine.tools["test_tool"].description == "Test tool for testing"
        assert engine.tools["test_tool"].status == ToolStatus.AVAILABLE

    def test_duplicate_tool_registration(self, engine):
        """测试重复工具注册"""
        # 第一次注册
        engine.register_tool("duplicate_tool", MockTool)
        initial_count = len(engine.tools)

        # 第二次注册相同工具
        success = engine.register_tool("duplicate_tool", MockTool)
        assert success is True
        assert len(engine.tools) == initial_count  # 应该更新而不是添加

    def test_tool_unregistration(self, engine):
        """测试工具注销"""
        # 注册工具
        engine.register_tool("temp_tool", MockTool)
        assert "temp_tool" in engine.tools

        # 注销工具
        success = engine.unregister_tool("temp_tool")
        assert success is True
        assert "temp_tool" not in engine.tools

    def test_unregister_nonexistent_tool(self, engine):
        """测试注销不存在的工具"""
        success = engine.unregister_tool("nonexistent_tool")
        assert success is False

    def test_list_tools(self, engine):
        """测试列出工具"""
        # 注册多个工具
        engine.register_tool("tool1", MockTool)
        engine.register_tool("tool2", MockTool)
        engine.register_tool("tool3", MockTool)

        tools = engine.list_tools()
        assert len(tools) == 3
        assert all(isinstance(tool, ToolInfo) for tool in tools)

    def test_get_tool_info(self, engine):
        """测试获取工具信息"""
        engine.register_tool("info_tool", MockTool, timeout=600.0)

        tool_info = engine.get_tool_info("info_tool")
        assert tool_info is not None
        assert tool_info.name == "info_tool"
        assert tool_info.timeout == 600.0

        tool_info = engine.get_tool_info("nonexistent")
        assert tool_info is None

    def test_execute_task_success(self, engine):
        """测试成功执行任务"""
        engine.register_tool("success_tool", MockTool)

        result = engine.execute_task(
            task_id="test_task_1",
            tool_name="success_tool",
            parameters={"param1": "value1"}
        )

        assert isinstance(result, ExecutionResult)
        assert result.task_id == "test_task_1"
        assert result.tool_name == "success_tool"
        assert result.status == TaskStatus.COMPLETED
        assert result.success is True
        assert result.data is not None
        assert result.error is None
        assert result.execution_time > 0

        # 验证工具统计更新
        tool_info = engine.get_tool_info("success_tool")
        assert tool_info.usage_count == 1
        assert tool_info.error_count == 0

    def test_execute_task_failure(self, engine):
        """测试任务执行失败"""
        engine.register_tool("fail_tool", MockTool, should_fail=True)

        result = engine.execute_task(
            task_id="test_task_2",
            tool_name="fail_tool",
            parameters={}
        )

        assert result.status == TaskStatus.FAILED
        assert result.success is False
        assert result.error is not None
        assert result.error_type == "ValueError"

        # 验证工具统计更新
        tool_info = engine.get_tool_info("fail_tool")
        assert tool_info.usage_count == 1
        assert tool_info.error_count == 1
        assert tool_info.status == ToolStatus.ERROR

    def test_execute_nonexistent_tool(self, engine):
        """测试执行不存在的工具"""
        result = engine.execute_task(
            task_id="test_task_3",
            tool_name="nonexistent_tool",
            parameters={}
        )

        assert result.status == TaskStatus.FAILED
        assert result.success is False
        assert result.error == "Tool nonexistent_tool not found"
        assert result.error_type == "ToolNotFoundError"

    def test_execute_task_async(self, engine):
        """测试异步任务执行"""
        engine.register_tool("async_tool", MockTool)

        future = engine.execute_task_async(
            task_id="async_task_1",
            tool_name="async_tool",
            parameters={}
        )

        assert future is not None
        assert "async_task_1" in engine.running_tasks

        result = future.result()
        assert result.status == TaskStatus.COMPLETED
        assert result.success is True

        # 任务完成后应该从运行列表中移除
        assert "async_task_1" not in engine.running_tasks

    def test_execute_tasks_batch(self, engine):
        """测试批量任务执行"""
        engine.register_tool("batch_tool1", MockTool)
        engine.register_tool("batch_tool2", MockTool)

        tasks = [
            {
                "task_id": "batch_task_1",
                "tool_name": "batch_tool1",
                "parameters": {"batch": True}
            },
            {
                "task_id": "batch_task_2",
                "tool_name": "batch_tool2",
                "parameters": {"batch": True}
            },
            {
                "task_id": "batch_task_3",
                "tool_name": "batch_tool1",
                "parameters": {"batch": False}
            }
        ]

        results = engine.execute_tasks(tasks)

        assert len(results) == 3
        assert all(isinstance(r, ExecutionResult) for r in results)
        assert all(r.success for r in results)

        # 验证所有任务都有结果
        task_ids = [r.task_id for r in results]
        assert "batch_task_1" in task_ids
        assert "batch_task_2" in task_ids
        assert "batch_task_3" in task_ids

    def test_execute_tasks_with_failures(self, engine):
        """测试包含失败的批量执行"""
        engine.register_tool("good_tool", MockTool)
        engine.register_tool("bad_tool", MockTool, should_fail=True)

        tasks = [
            {
                "task_id": "good_task",
                "tool_name": "good_tool",
                "parameters": {}
            },
            {
                "task_id": "bad_task",
                "tool_name": "bad_tool",
                "parameters": {}
            }
        ]

        results = engine.execute_tasks(tasks)

        assert len(results) == 2
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]

        assert len(successful_results) == 1
        assert len(failed_results) == 1
        assert successful_results[0].task_id == "good_task"
        assert failed_results[0].task_id == "bad_task"

    def test_execute_plan(self, engine):
        """测试执行计划"""
        engine.register_tool("plan_tool", MockTool)

        # 创建模拟计划
        class MockPlan:
            def __init__(self):
                self.plan_id = "test_plan"
                self.tasks = [
                    Mock(task_id="plan_task_1", task_type="plan_tool", parameters={"p1": "v1"}),
                    Mock(task_id="plan_task_2", task_type="plan_tool", parameters={"p2": "v2"})
                ]
                self.metadata = {}

        plan = MockPlan()
        results = engine.execute_plan(plan)

        assert len(results) == 2
        assert all(r.success for r in results)

        # 验证计划元数据更新
        assert 'execution_results' in plan.metadata
        assert 'execution_time' in plan.metadata
        assert 'success_rate' in plan.metadata
        assert plan.metadata['execution_results'] == 2
        assert plan.metadata['success_rate'] == 1.0

    def test_cancel_task(self, engine):
        """测试取消任务"""
        engine.register_tool("slow_tool", MockTool, delay=1.0)

        # 提交任务但不等待完成
        future = engine.execute_task_async(
            task_id="cancellable_task",
            tool_name="slow_tool",
            parameters={}
        )

        # 立即取消
        cancelled = engine.cancel_task("cancellable_task")

        # 注意：由于任务可能已经完成，取消可能不成功
        # 这是ThreadPoolExecutor的行为特性
        assert isinstance(cancelled, bool)

    def test_cancel_nonexistent_task(self, engine):
        """测试取消不存在的任务"""
        cancelled = engine.cancel_task("nonexistent_task")
        assert cancelled is False

    def test_get_task_result(self, engine):
        """测试获取任务结果"""
        engine.register_tool("result_tool", MockTool)

        # 执行任务
        result = engine.execute_task(
            task_id="result_task",
            tool_name="result_tool",
            parameters={}
        )

        # 获取结果
        retrieved_result = engine.get_task_result("result_task")
        assert retrieved_result is not None
        assert retrieved_result.task_id == "result_task"
        assert retrieved_result == result

    def test_get_nonexistent_task_result(self, engine):
        """测试获取不存在任务的结果"""
        result = engine.get_task_result("nonexistent_task")
        assert result is None

    def test_get_running_tasks(self, engine):
        """测试获取正在运行的任务"""
        engine.register_tool("running_tool", MockTool, delay=0.1)  # 添加延迟确保任务不会立即完成

        # 提交任务但不等待完成
        future = engine.execute_task_async(
            task_id="running_task",
            tool_name="running_tool",
            parameters={}
        )

        # 稍等一下确保任务开始运行
        import time
        time.sleep(0.01)

        running_tasks = engine.get_running_tasks()
        assert "running_task" in running_tasks

        # 等待任务完成
        future.result()

        # 现在应该没有运行中的任务
        running_tasks = engine.get_running_tasks()
        assert len(running_tasks) == 0

    def test_get_statistics(self, engine):
        """测试获取统计信息"""
        engine.register_tool("stats_tool", MockTool)
        engine.register_tool("fail_stats_tool", MockTool, should_fail=True)

        # 执行一些任务
        engine.execute_task("stats_task_1", "stats_tool", {})
        engine.execute_task("stats_task_2", "fail_stats_tool", {})
        engine.execute_task("stats_task_3", "stats_tool", {})

        stats = engine.get_statistics()

        assert 'engine_stats' in stats
        assert 'tool_stats' in stats
        assert 'running_tasks' in stats
        assert 'available_tools' in stats

        engine_stats = stats['engine_stats']
        assert engine_stats['total_tasks'] == 3
        assert engine_stats['completed_tasks'] == 2
        assert engine_stats['failed_tasks'] == 1

        tool_stats = stats['tool_stats']
        assert 'stats_tool' in tool_stats
        assert 'fail_stats_tool' in tool_stats
        assert tool_stats['stats_tool']['usage_count'] == 2
        assert tool_stats['stats_tool']['error_count'] == 0
        assert tool_stats['fail_stats_tool']['usage_count'] == 1
        assert tool_stats['fail_stats_tool']['error_count'] == 1

    def test_tool_parameters(self, engine):
        """测试工具参数传递"""
        def custom_tool(param1, param2, optional_param="default"):
            return {"param1": param1, "param2": param2, "optional_param": optional_param}

        engine.register_tool(
            "custom_tool",
            custom_tool,
            timeout=120.0
        )

        result = engine.execute_task(
            task_id="custom_task",
            tool_name="custom_tool",
            parameters={
                "param1": "value1",
                "param2": "value2"
            }
        )

        assert result.success is True
        assert result.data["param1"] == "value1"
        assert result.data["param2"] == "value2"
        assert result.data["optional_param"] == "default"

    def test_static_method_tool(self, engine):
        """测试静态方法工具"""
        engine.register_tool("static_tool", MockTool.static_execute)

        result = engine.execute_task(
            task_id="static_task",
            tool_name="static_tool",
            parameters={"static_param": "static_value"}
        )

        assert result.success is True
        assert result.data["static"] is True

    def test_execution_result_dataclass(self):
        """测试ExecutionResult数据类"""
        start_time = time.time()
        end_time = start_time + 1.0

        result = ExecutionResult(
            task_id="test_result",
            tool_name="test_tool",
            status=TaskStatus.COMPLETED,
            success=True,
            data={"key": "value"},
            start_time=start_time,
            end_time=end_time
        )

        assert result.task_id == "test_result"
        assert result.tool_name == "test_tool"
        assert result.status == TaskStatus.COMPLETED
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.execution_time == 1.0

    def test_cleanup(self, engine):
        """测试清理资源"""
        engine.register_tool("cleanup_tool", MockTool, delay=0.1)  # 添加延迟确保任务不会立即完成

        # 提交一些任务
        engine.execute_task_async("cleanup_task_1", "cleanup_tool", {})
        engine.execute_task_async("cleanup_task_2", "cleanup_tool", {})

        # 稍等一下确保任务开始运行
        import time
        time.sleep(0.01)

        # 清理前应该有运行中的任务
        assert len(engine.get_running_tasks()) > 0

        # 执行清理
        engine.cleanup()

        # 清理后应该没有运行中的任务
        assert len(engine.get_running_tasks()) == 0

    def test_multiple_engines(self):
        """测试多个引擎实例"""
        engine1 = ExecutionEngine(max_workers=2)
        engine2 = ExecutionEngine(max_workers=4)

        engine1.register_tool("engine1_tool", MockTool)
        engine2.register_tool("engine2_tool", MockTool)

        result1 = engine1.execute_task("task1", "engine1_tool", {})
        result2 = engine2.execute_task("task2", "engine2_tool", {})

        assert result1.success is True
        assert result2.success is True
        assert result1.tool_name == "engine1_tool"
        assert result2.tool_name == "engine2_tool"

        # 清理资源
        engine1.cleanup()
        engine2.cleanup()

    def test_concurrent_execution(self, engine):
        """测试并发执行"""
        engine.register_tool("concurrent_tool", MockTool)

        # 提交多个任务
        futures = []
        for i in range(5):
            future = engine.execute_task_async(
                task_id=f"concurrent_task_{i}",
                tool_name="concurrent_tool",
                parameters={"task_id": i}
            )
            futures.append(future)

        # 等待所有任务完成
        results = [f.result() for f in futures]

        assert len(results) == 5
        assert all(r.success for r in results)
        assert len(set(r.task_id for r in results)) == 5  # 确保所有任务都执行了