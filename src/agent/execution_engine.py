"""
执行引擎模块
负责任务执行、工具调用和结果收集
"""

import os
import time
import asyncio
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future, as_completed

from ..utils.logger import get_logger
from ..utils.config import get_config_manager


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolStatus(Enum):
    """工具状态枚举"""
    REGISTERED = "registered"
    AVAILABLE = "available"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class ExecutionResult:
    """执行结果数据结构"""
    task_id: str
    tool_name: str
    status: TaskStatus
    success: bool
    data: Any = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    execution_time: float = 0.0
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """后处理初始化"""
        if self.end_time > 0:
            self.execution_time = self.end_time - self.start_time


@dataclass
class ToolInfo:
    """工具信息数据结构"""
    name: str
    description: str
    tool_class: Callable
    status: ToolStatus = ToolStatus.REGISTERED
    last_used: float = 0.0
    usage_count: int = 0
    error_count: int = 0
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 300.0  # 默认5分钟超时
    is_async: bool = False


class ExecutionEngine:
    """执行引擎"""

    def __init__(self, config_manager=None, max_workers: int = 4):
        """
        初始化执行引擎

        Args:
            config_manager: 配置管理器实例
            max_workers: 最大工作线程数
        """
        self.logger = get_logger()
        self.config_manager = config_manager or get_config_manager()

        # 引擎配置
        self.config = self.config_manager.get_section('execution_engine')

        # 工具注册表
        self.tools: Dict[str, ToolInfo] = {}

        # 执行器配置
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # 执行状态
        self.running_tasks: Dict[str, Future] = {}
        self.completed_tasks: Dict[str, ExecutionResult] = {}

        # 统计信息
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'total_execution_time': 0.0
        }

        self.logger.info(f"ExecutionEngine initialized with {max_workers} workers")

    def register_tool(self,
                     name: str,
                     tool_class: Callable,
                     description: str = "",
                     timeout: float = 300.0,
                     is_async: bool = False,
                     **kwargs) -> bool:
        """
        注册工具

        Args:
            name: 工具名称
            tool_class: 工具类或函数
            description: 工具描述
            timeout: 超时时间（秒）
            is_async: 是否为异步工具
            **kwargs: 额外参数

        Returns:
            注册是否成功
        """
        try:
            if name in self.tools:
                self.logger.warning(f"Tool {name} already registered, updating...")

            # 检查工具类型并存储实例或函数
            tool_instance = tool_class
            if hasattr(tool_class, '__call__') and not isinstance(tool_class, type):
                # 如果是可调用对象（函数或实例）
                tool_instance = tool_class
            elif isinstance(tool_class, type):
                # 如果是类，尝试实例化
                try:
                    tool_instance = tool_class(**kwargs)
                except TypeError:
                    # 如果实例化失败，保持类引用
                    tool_instance = tool_class

            tool_info = ToolInfo(
                name=name,
                description=description,
                tool_class=tool_instance,
                status=ToolStatus.AVAILABLE,
                timeout=timeout,
                is_async=is_async,
                parameters=kwargs
            )

            self.tools[name] = tool_info
            self.logger.info(f"Tool {name} registered successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to register tool {name}: {e}")
            return False

    def unregister_tool(self, name: str) -> bool:
        """
        注销工具

        Args:
            name: 工具名称

        Returns:
            注销是否成功
        """
        if name in self.tools:
            del self.tools[name]
            self.logger.info(f"Tool {name} unregistered successfully")
            return True
        else:
            self.logger.warning(f"Tool {name} not found")
            return False

    def get_tool_info(self, name: str) -> Optional[ToolInfo]:
        """
        获取工具信息

        Args:
            name: 工具名称

        Returns:
            工具信息对象
        """
        return self.tools.get(name)

    def list_tools(self) -> List[ToolInfo]:
        """
        列出所有已注册的工具

        Returns:
            工具信息列表
        """
        return list(self.tools.values())

    def execute_task(self, task_id: str, tool_name: str, parameters: Dict[str, Any]) -> ExecutionResult:
        """
        执行单个任务

        Args:
            task_id: 任务ID
            tool_name: 工具名称
            parameters: 工具参数

        Returns:
            执行结果
        """
        start_time = time.time()

        # 验证工具是否存在
        if tool_name not in self.tools:
            result = ExecutionResult(
                task_id=task_id,
                tool_name=tool_name,
                status=TaskStatus.FAILED,
                success=False,
                error=f"Tool {tool_name} not found",
                error_type="ToolNotFoundError",
                start_time=start_time,
                end_time=time.time()
            )
            self._record_result(result)
            return result

        tool_info = self.tools[tool_name]

        # 更新工具状态
        tool_info.status = ToolStatus.BUSY
        tool_info.last_used = start_time

        try:
            self.logger.info(f"Executing task {task_id} with tool {tool_name}")

            # 执行工具
            if tool_info.is_async:
                # 异步工具执行
                if hasattr(tool_info.tool_class, 'execute'):
                    if callable(tool_info.tool_class.execute):
                        data = asyncio.run(tool_info.tool_class.execute(**parameters))
                    else:
                        raise AttributeError("execute method is not callable")
                elif callable(tool_info.tool_class):
                    data = asyncio.run(tool_info.tool_class(**parameters))
                else:
                    raise TypeError("Tool is not callable")
            else:
                # 同步工具执行
                if hasattr(tool_info.tool_class, 'execute'):
                    if callable(tool_info.tool_class.execute):
                        data = tool_info.tool_class.execute(**parameters)
                    else:
                        raise AttributeError("execute method is not callable")
                elif callable(tool_info.tool_class):
                    data = tool_info.tool_class(**parameters)
                else:
                    raise TypeError("Tool is not callable")

            # 执行成功
            end_time = time.time()
            result = ExecutionResult(
                task_id=task_id,
                tool_name=tool_name,
                status=TaskStatus.COMPLETED,
                success=True,
                data=data,
                execution_time=end_time - start_time,
                start_time=start_time,
                end_time=end_time
            )

            # 更新工具统计
            tool_info.usage_count += 1
            tool_info.status = ToolStatus.AVAILABLE

            self.logger.info(f"Task {task_id} completed successfully in {result.execution_time:.2f}s")

        except Exception as e:
            # 执行失败
            end_time = time.time()
            error_type = type(e).__name__

            result = ExecutionResult(
                task_id=task_id,
                tool_name=tool_name,
                status=TaskStatus.FAILED,
                success=False,
                error=str(e),
                error_type=error_type,
                execution_time=end_time - start_time,
                start_time=start_time,
                end_time=end_time
            )

            # 更新工具统计
            tool_info.usage_count += 1
            tool_info.error_count += 1
            tool_info.status = ToolStatus.ERROR

            self.logger.error(f"Task {task_id} failed: {e}")

        # 记录结果
        self._record_result(result)
        return result

    def execute_task_async(self, task_id: str, tool_name: str, parameters: Dict[str, Any]) -> Future:
        """
        异步执行任务

        Args:
            task_id: 任务ID
            tool_name: 工具名称
            parameters: 工具参数

        Returns:
            Future对象
        """
        future = self.executor.submit(self.execute_task, task_id, tool_name, parameters)
        self.running_tasks[task_id] = future

        def callback(fut: Future):
            """任务完成回调"""
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]

        future.add_done_callback(callback)
        return future

    def execute_tasks(self, tasks: List[Dict[str, Any]]) -> List[ExecutionResult]:
        """
        批量执行任务

        Args:
            tasks: 任务列表，每个任务包含 task_id, tool_name, parameters

        Returns:
            执行结果列表
        """
        results = []

        self.logger.info(f"Executing {len(tasks)} tasks")

        # 提交所有任务
        futures = []
        for task in tasks:
            task_id = task.get('task_id')
            tool_name = task.get('tool_name')
            parameters = task.get('parameters', {})

            if task_id and tool_name:
                future = self.execute_task_async(task_id, tool_name, parameters)
                futures.append(future)

        # 等待所有任务完成
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                self.logger.error(f"Task execution failed: {e}")

        self.logger.info(f"Completed {len(results)} tasks with {len([r for r in results if r.success])} successes")
        return results

    def execute_plan(self, plan) -> List[ExecutionResult]:
        """
        执行完整的执行计划

        Args:
            plan: 执行计划对象

        Returns:
            执行结果列表
        """
        self.logger.info(f"Executing plan {plan.plan_id} with {len(plan.tasks)} tasks")

        # 构建任务列表
        tasks = []
        for task in plan.tasks:
            task_data = {
                'task_id': task.task_id,
                'tool_name': task.task_type,
                'parameters': task.parameters
            }
            tasks.append(task_data)

        # 执行所有任务
        results = self.execute_tasks(tasks)

        # 更新计划统计
        plan.metadata['execution_results'] = len(results)
        plan.metadata['execution_time'] = sum(r.execution_time for r in results)
        plan.metadata['success_rate'] = len([r for r in results if r.success]) / len(results) if results else 0

        return results

    def cancel_task(self, task_id: str) -> bool:
        """
        取消正在执行的任务

        Args:
            task_id: 任务ID

        Returns:
            取消是否成功
        """
        if task_id in self.running_tasks:
            future = self.running_tasks[task_id]
            cancelled = future.cancel()

            # 从运行任务列表中移除，无论是否成功取消
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]

            if cancelled:
                self.logger.info(f"Task {task_id} cancelled")

                # 记录取消结果
                result = ExecutionResult(
                    task_id=task_id,
                    tool_name="unknown",
                    status=TaskStatus.CANCELLED,
                    success=False,
                    error="Task cancelled by user",
                    error_type="CancelledError"
                )
                self._record_result(result)

            return cancelled
        else:
            self.logger.warning(f"Task {task_id} not found in running tasks")
            return False

    def get_task_result(self, task_id: str) -> Optional[ExecutionResult]:
        """
        获取任务执行结果

        Args:
            task_id: 任务ID

        Returns:
            执行结果对象
        """
        return self.completed_tasks.get(task_id)

    def get_running_tasks(self) -> List[str]:
        """
        获取正在运行的任务列表

        Returns:
            任务ID列表
        """
        return list(self.running_tasks.keys())

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取执行统计信息

        Returns:
            统计信息字典
        """
        # 更新统计信息
        self.stats['total_tasks'] = len(self.completed_tasks)
        self.stats['completed_tasks'] = len([r for r in self.completed_tasks.values() if r.success])
        self.stats['failed_tasks'] = len([r for r in self.completed_tasks.values() if not r.success])
        self.stats['total_execution_time'] = sum(r.execution_time for r in self.completed_tasks.values())

        # 工具统计
        tool_stats = {}
        for name, tool in self.tools.items():
            tool_stats[name] = {
                'usage_count': tool.usage_count,
                'error_count': tool.error_count,
                'success_rate': (tool.usage_count - tool.error_count) / tool.usage_count if tool.usage_count > 0 else 0,
                'last_used': tool.last_used,
                'status': tool.status.value
            }

        return {
            'engine_stats': self.stats.copy(),
            'tool_stats': tool_stats,
            'running_tasks': len(self.running_tasks),
            'available_tools': len([t for t in self.tools.values() if t.status == ToolStatus.AVAILABLE])
        }

    def _record_result(self, result: ExecutionResult):
        """
        记录执行结果

        Args:
            result: 执行结果
        """
        self.completed_tasks[result.task_id] = result
        self.logger.debug(f"Recorded result for task {result.task_id}")

    def cleanup(self):
        """
        清理资源
        """
        self.logger.info("Cleaning up execution engine")

        # 取消所有运行中的任务
        for task_id in list(self.running_tasks.keys()):
            self.cancel_task(task_id)

        # 关闭执行器
        self.executor.shutdown(wait=True)

        self.logger.info("Execution engine cleaned up")

    def __del__(self):
        """析构函数"""
        try:
            self.cleanup()
        except:
            pass