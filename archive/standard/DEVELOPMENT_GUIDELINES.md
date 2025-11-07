# Fix_agent - 开发指南

## 开发目标
本指南为Fix_agent的开发提供统一的规范和最佳实践，确保代码质量、接口一致性和系统可维护性。

---

## 核心开发原则

### 1. SOLID原则
- **单一职责原则 (SRP)**: 每个类只负责一个功能
- **开闭原则 (OCP)**: 对扩展开放，对修改关闭
- **里氏替换原则 (LSP)**: 子类可以替换父类
- **接口隔离原则 (ISP)**: 接口应该最小化
- **依赖倒置原则 (DIP)**: 依赖抽象而非具体实现

### 2. 架构原则
- **分层架构**: 清晰的层次划分
- **模块化设计**: 高内聚低耦合
- **接口驱动**: 基于接口编程
- **事件驱动**: 基于消息的异步通信
- **可测试性**: 支持单元测试和集成测试

### 3. 代码质量原则
- **可读性**: 代码自文档化
- **可维护性**: 易于修改和扩展
- **可重用性**: 组件化设计
- **性能优化**: 合理的资源使用
- **安全第一**: 数据和系统安全

---

## 项目结构规范

### 目录结构
```
src/
├── agent/                  # Agent相关模块
│   ├── __init__.py
│   ├── base_agent.py      # Agent基类
│   ├── perception_module.py
│   ├── decision_module.py
│   ├── execution_module.py
│   ├── agent_registry.py
│   ├── agent_factory.py
│   └── message_handler.py
├── communication/          # 通信模块
│   ├── __init__.py
│   ├── message.py         # 消息数据结构
│   ├── message_queue.py   # 消息队列
│   ├── message_router.py  # 消息路由
│   └── event_bus.py       # 事件总线
├── llm/                    # LLM集成模块
│   ├── __init__.py
│   ├── base.py            # LLM基础接口
│   ├── client.py          # LLM客户端
│   ├── providers/         # LLM提供商
│   └── response_parser.py
├── tools/                  # 工具系统
│   ├── __init__.py
│   ├── base_tool.py       # 工具基类
│   ├── tool_registry.py   # 工具注册表
│   ├── perception/        # 感知工具
│   ├── decision/          # 决策工具
│   └── execution/         # 执行工具
├── workflow/               # 工作流引擎
│   ├── __init__.py
│   ├── engine.py          # 工作流引擎
│   ├── state_machine.py   # 状态机
│   └── task_queue.py      # 任务队列
├── context/                # 上下文管理
│   ├── __init__.py
│   ├── session_context.py
│   ├── project_context.py
│   └── conversation_history.py
├── interfaces/             # 用户接口
│   ├── __init__.py
│   ├── cli/               # 命令行接口
│   ├── web/               # Web接口
│   └── api/               # REST API
├── utils/                  # 工具类
│   ├── __init__.py
│   ├── config_manager.py  # 配置管理
│   ├── logger.py          # 日志系统
│   ├── helpers.py         # 辅助函数
│   ├── exceptions.py      # 异常定义
│   └── validators.py      # 验证器
└── tests/                  # 测试模块
    ├── test_agent/
    ├── test_communication/
    ├── test_llm/
    ├── test_tools/
    ├── test_workflow/
    └── test_integration/
```

### 命名规范
- **文件名**: 小写字母+下划线 (snake_case)
- **类名**: 大驼峰命名 (PascalCase)
- **方法名**: 小驼峰命名 (camelCase)
- **常量**: 大写字母+下划线 (UPPER_SNAKE_CASE)
- **接口**: 以'I'开头 (如IAgent)

---

## 编码规范

### Python编码标准
```python
# 导入顺序
import os
import sys
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

# 第三方库
import asyncio
import aiofiles

# 本地模块
from .base_interface import IBaseInterface
from ..utils.exceptions import CustomException

# 类定义
class AgentExample:
    """Agent示例类

    这个类演示了标准的类定义格式

    Attributes:
        agent_id: Agent的唯一标识
        config: Agent配置信息
        status: Agent当前状态
    """

    def __init__(self, agent_id: str, config: Dict[str, Any]):
        """初始化Agent

        Args:
            agent_id: Agent唯一标识
            config: 配置信息字典

        Raises:
            ValueError: 当agent_id为空时
            ConfigError: 当配置无效时
        """
        self.agent_id = agent_id
        self.config = config
        self.status = AgentStatus.INITIALIZING

    async def process_task(self, task: Task) -> Dict[str, Any]:
        """处理任务

        Args:
            task: 要处理的任务对象

        Returns:
            处理结果字典

        Raises:
            TaskError: 任务处理失败时
            TimeoutError: 任务超时时
        """
        try:
            # 实现逻辑
            result = await self._execute_task(task)
            return result
        except Exception as e:
            logger.error(f"Task processing failed: {e}")
            raise TaskError(f"Failed to process task {task.task_id}") from e

    async def _execute_task(self, task: Task) -> Dict[str, Any]:
        """私有方法：执行任务具体逻辑"""
        # 实现细节
        pass
```

### 异步编程规范
```python
import asyncio
from typing import AsyncGenerator

class AsyncService:
    """异步服务示例"""

    async def process_with_timeout(self, data: Any, timeout: float = 30.0) -> Any:
        """带超时的异步处理"""
        try:
            result = await asyncio.wait_for(
                self._process_data(data),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Processing timeout after {timeout}s")
            raise

    async def process_batch(self, items: List[Any]) -> List[Any]:
        """批量异步处理"""
        semaphore = asyncio.Semaphore(10)  # 限制并发数

        async def process_single(item: Any) -> Any:
            async with semaphore:
                return await self._process_data(item)

        tasks = [process_single(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常结果
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch processing error: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)

        return processed_results

    async def stream_process(self, data_stream: AsyncGenerator[Any, None]) -> AsyncGenerator[Any, None]:
        """流式异步处理"""
        async for data in data_stream:
            try:
                processed = await self._process_data(data)
                yield processed
            except Exception as e:
                logger.error(f"Stream processing error: {e}")
                continue
```

### 错误处理规范
```python
# 自定义异常类
class AgentError(Exception):
    """Agent基础异常"""
    pass

class TaskError(AgentError):
    """任务处理异常"""
    def __init__(self, message: str, task_id: str = None, error_code: str = None):
        super().__init__(message)
        self.task_id = task_id
        self.error_code = error_code

class CommunicationError(AgentError):
    """通信异常"""
    pass

# 错误处理示例
class RobustService:
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """健壮的请求处理"""
        try:
            # 验证请求
            if not self._validate_request(request):
                raise ValueError("Invalid request format")

            # 处理请求
            result = await self._process_request(request)

            # 验证结果
            if not self._validate_result(result):
                raise ProcessingError("Invalid processing result")

            return result

        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            return {"error": "validation_failed", "message": str(e)}

        except ProcessingError as e:
            logger.error(f"Processing error: {e}")
            return {"error": "processing_failed", "message": str(e)}

        except Exception as e:
            logger.critical(f"Unexpected error: {e}")
            return {"error": "internal_error", "message": "An unexpected error occurred"}
```

---

## 接口实现规范

### 接口实现模板
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class IAgentService(ABC):
    """Agent服务接口"""

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化服务"""
        pass

    @abstractmethod
    async def start(self) -> bool:
        """启动服务"""
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """停止服务"""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        pass

class ConcreteAgentService(IAgentService):
    """具体的Agent服务实现"""

    def __init__(self):
        self._initialized = False
        self._running = False
        self._config = {}

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """实现初始化逻辑"""
        try:
            self._config = config
            # 执行初始化步骤
            await self._setup_components()
            self._initialized = True
            logger.info("Agent service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    async def start(self) -> bool:
        """实现启动逻辑"""
        if not self._initialized:
            logger.error("Service not initialized")
            return False

        try:
            # 启动服务组件
            await self._start_components()
            self._running = True
            logger.info("Agent service started successfully")
            return True
        except Exception as e:
            logger.error(f"Start failed: {e}")
            return False

    # ... 其他方法的实现
```

### 数据验证规范
```python
from pydantic import BaseModel, validator
from typing import List, Optional

class TaskRequest(BaseModel):
    """任务请求模型"""
    task_type: str
    description: str
    parameters: Dict[str, Any] = {}
    priority: int = 5

    @validator('task_type')
    def validate_task_type(cls, v):
        allowed_types = ['analysis', 'repair', 'verification', 'report']
        if v not in allowed_types:
            raise ValueError(f"Task type must be one of {allowed_types}")
        return v

    @validator('priority')
    def validate_priority(cls, v):
        if not 1 <= v <= 10:
            raise ValueError("Priority must be between 1 and 10")
        return v

    @validator('description')
    def validate_description(cls, v):
        if len(v.strip()) == 0:
            raise ValueError("Description cannot be empty")
        if len(v) > 500:
            raise ValueError("Description too long (max 500 characters)")
        return v.strip()

# 使用示例
def create_task_from_request(request_data: Dict[str, Any]) -> Task:
    """从请求数据创建任务对象"""
    try:
        task_request = TaskRequest(**request_data)

        task = Task(
            task_type=task_request.task_type,
            description=task_request.description,
            parameters=task_request.parameters,
            priority=task_request.priority
        )

        return task

    except Exception as e:
        logger.error(f"Invalid task request: {e}")
        raise ValueError(f"Invalid task request: {e}")
```

---

## 测试规范

### 单元测试模板
```python
import unittest
from unittest.mock import Mock, AsyncMock, patch
import pytest
from datetime import datetime

class TestAgentService(unittest.TestCase):
    """Agent服务单元测试"""

    def setUp(self):
        """测试前置设置"""
        self.service = ConcreteAgentService()
        self.test_config = {
            "agent_id": "test_agent",
            "max_tasks": 10,
            "timeout": 30.0
        }

    async def asyncSetUp(self):
        """异步测试前置设置"""
        await self.service.initialize(self.test_config)

    def test_initialization_success(self):
        """测试成功初始化"""
        result = asyncio.run(self.service.initialize(self.test_config))
        self.assertTrue(result)
        self.assertTrue(self.service._initialized)

    def test_initialization_invalid_config(self):
        """测试无效配置的初始化"""
        invalid_config = {}  # 空配置
        result = asyncio.run(self.service.initialize(invalid_config))
        self.assertFalse(result)

    @patch('src.agent.concrete_agent_service.logger')
    async def test_start_without_initialization(self, mock_logger):
        """测试未初始化时启动"""
        result = await self.service.start()
        self.assertFalse(result)
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_async_operation(self):
        """测试异步操作"""
        await self.asyncSetUp()

        result = await self.service.process_task({
            "type": "test_task",
            "data": "test_data"
        })

        self.assertIsNotNone(result)
        self.assertIn("status", result)

# 集成测试示例
class TestAgentIntegration(unittest.TestCase):
    """Agent集成测试"""

    async def test_full_workflow(self):
        """测试完整工作流"""
        # 设置测试环境
        agent = await self._setup_test_agent()

        # 执行工作流
        task = Task(
            task_type="code_analysis",
            description="Analyze Python code",
            parameters={"file_path": "test.py"}
        )

        result = await agent.process_task(task)

        # 验证结果
        self.assertEqual(result["status"], "success")
        self.assertIn("analysis_data", result)

        # 清理测试环境
        await agent.stop()
```

### 性能测试规范
```python
import time
import asyncio
from typing import List

class PerformanceTest:
    """性能测试工具"""

    @staticmethod
    async def measure_execution_time(func, *args, **kwargs) -> tuple:
        """测量函数执行时间"""
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            return result, execution_time
        except Exception as e:
            execution_time = time.time() - start_time
            raise e

    @staticmethod
    async def benchmark_concurrent_operations(
        operation,
        num_operations: int = 100,
        max_concurrent: int = 10
    ) -> Dict[str, float]:
        """并发操作基准测试"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def limited_operation():
            async with semaphore:
                return await operation()

        start_time = time.time()
        tasks = [limited_operation() for _ in range(num_operations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time

        successful_operations = sum(1 for r in results if not isinstance(r, Exception))

        return {
            "total_time": total_time,
            "operations_per_second": num_operations / total_time,
            "success_rate": successful_operations / num_operations,
            "average_time_per_operation": total_time / num_operations
        }
```

---

## 部署和运维规范

### 配置管理
```python
# config/settings.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    app_name: str = "AI Agent System"
    debug: bool = False
    version: str = "1.0.0"

    # 服务配置
    host: str = "localhost"
    port: int = 8000

    # 数据库配置
    database_url: str
    database_pool_size: int = 10

    # Redis配置
    redis_url: str = "redis://localhost:6379"

    # LLM配置
    openai_api_key: Optional[str] = None
    default_model: str = "gpt-3.5-turbo"

    # 日志配置
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    class Config:
        env_file = ".env"
        case_sensitive = False

# 使用配置
settings = Settings()
```

### 日志配置
```python
import logging
import sys
from pathlib import Path

def setup_logging(
    level: str = "INFO",
    log_file: str = None,
    format_string: str = None
) -> None:
    """设置日志配置"""

    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 配置日志格式
    formatter = logging.Formatter(format_string)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # 文件处理器
    handlers = [console_handler]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # 配置根日志器
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=handlers
    )

    # 设置第三方库日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
```

### 监控和指标
```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time
from functools import wraps

# 定义指标
task_counter = Counter('tasks_processed_total', 'Total processed tasks', ['task_type', 'status'])
task_duration = Histogram('task_processing_seconds', 'Task processing time')
active_agents = Gauge('active_agents_count', 'Number of active agents')

def monitor_performance(func):
    """性能监控装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        task_type = kwargs.get('task_type', 'unknown')

        try:
            result = await func(*args, **kwargs)
            task_counter.labels(task_type=task_type, status='success').inc()
            return result
        except Exception as e:
            task_counter.labels(task_type=task_type, status='error').inc()
            raise
        finally:
            task_duration.observe(time.time() - start_time)

    return wrapper

# 启动监控服务器
def start_metrics_server(port: int = 8001):
    """启动指标监控服务器"""
    start_http_server(port)
```

---

## 文档规范

### 代码文档
```python
def complex_algorithm(
    data: List[Dict[str, Any]],
    threshold: float = 0.5,
    max_iterations: int = 1000
) -> Dict[str, Any]:
    """复杂算法实现

    这个函数实现了复杂的数据分析算法，用于处理大量的结构化数据。

    Args:
        data: 输入数据列表，每个元素都是包含分析所需字段的字典
        threshold: 算法阈值，用于控制算法的敏感度，范围0-1
        max_iterations: 最大迭代次数，防止无限循环

    Returns:
        包含分析结果的字典，结构如下：
        {
            "status": "success|failed",
            "results": [
                {
                    "item_id": str,
                    "score": float,
                    "classification": str
                }
            ],
            "metadata": {
                "processing_time": float,
                "iterations": int,
                "convergence_reached": bool
            }
        }

    Raises:
        ValueError: 当输入数据为空或格式不正确时
        AlgorithmError: 当算法无法收敛时
        TimeoutError: 当处理时间过长时

    Example:
        >>> data = [{"id": "1", "value": 0.8}, {"id": "2", "value": 0.3}]
        >>> result = complex_algorithm(data, threshold=0.5)
        >>> print(result["status"])
        'success'
    """
    pass
```

### API文档
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="AI Agent API", version="1.0.0")

class TaskRequest(BaseModel):
    """任务请求模型"""
    task_type: str
    description: str
    parameters: Dict[str, Any] = {}
    priority: int = 5

class TaskResponse(BaseModel):
    """任务响应模型"""
    task_id: str
    status: str
    message: str
    result: Optional[Dict[str, Any]] = None

@app.post(
    "/api/v1/tasks",
    response_model=TaskResponse,
    summary="创建新任务",
    description="创建一个新的分析任务，系统会根据任务类型分配给合适的Agent处理",
    tags=["任务管理"]
)
async def create_task(request: TaskRequest) -> TaskResponse:
    """
    创建新任务

    - **task_type**: 任务类型 (analysis, repair, verification, report)
    - **description**: 任务描述
    - **parameters**: 任务参数
    - **priority**: 任务优先级 (1-10)

    返回任务ID和状态信息
    """
    pass
```

---

## 安全规范

### 输入验证
```python
import re
from typing import Any

class SecurityValidator:
    """安全验证器"""

    @staticmethod
    def validate_file_path(file_path: str) -> bool:
        """验证文件路径安全性"""
        # 防止路径遍历攻击
        if ".." in file_path or file_path.startswith("/"):
            return False

        # 只允许特定字符
        pattern = r'^[a-zA-Z0-9_\-./]+$'
        return bool(re.match(pattern, file_path))

    @staticmethod
    def validate_command_input(command: str) -> bool:
        """验证命令输入安全性"""
        # 危险命令黑名单
        dangerous_commands = [
            "rm", "delete", "format", "shutdown", "reboot",
            "sudo", "su", "passwd", "chmod", "chown"
        ]

        command_lower = command.lower()
        for dangerous in dangerous_commands:
            if dangerous in command_lower:
                return False

        return True

    @staticmethod
    def sanitize_input(user_input: str) -> str:
        """清理用户输入"""
        # 移除潜在的恶意字符
        dangerous_chars = ["<", ">", "&", "|", ";", "`", "$", "(", ")", "{", "}"]

        sanitized = user_input
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "")

        return sanitized.strip()
```

### 权限控制
```python
from enum import Enum
from typing import List, Optional

class Permission(Enum):
    """权限枚举"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"

class UserRole(Enum):
    """用户角色枚举"""
    GUEST = "guest"
    USER = "user"
    DEVELOPER = "developer"
    ADMIN = "admin"

class AccessControl:
    """访问控制"""

    ROLE_PERMISSIONS = {
        UserRole.GUEST: [Permission.READ],
        UserRole.USER: [Permission.READ, Permission.EXECUTE],
        UserRole.DEVELOPER: [Permission.READ, Permission.WRITE, Permission.EXECUTE],
        UserRole.ADMIN: [Permission.READ, Permission.WRITE, Permission.EXECUTE, Permission.ADMIN]
    }

    @classmethod
    def has_permission(cls, user_role: UserRole, required_permission: Permission) -> bool:
        """检查用户是否具有指定权限"""
        user_permissions = cls.ROLE_PERMISSIONS.get(user_role, [])
        return required_permission in user_permissions

    @staticmethod
    def require_permission(permission: Permission):
        """权限装饰器"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                user_role = kwargs.get('user_role')
                if not user_role or not AccessControl.has_permission(user_role, permission):
                    raise PermissionError(f"Insufficient permissions for {permission.value}")
                return await func(*args, **kwargs)
            return wrapper
        return decorator
```

---

## 最佳实践总结

### 开发流程
1. **需求分析**: 明确功能需求和技术约束
2. **接口设计**: 基于接口规范设计API
3. **实现编码**: 遵循编码规范实现功能
4. **单元测试**: 编写全面的测试用例
5. **集成测试**: 验证模块间协作
6. **代码审查**: 团队成员审查代码
7. **文档更新**: 更新相关文档

### 质量保证
- 代码审查必须通过
- 测试覆盖率不低于90%
- 性能测试通过基准
- 安全扫描无高危漏洞
- 文档完整且准确

### 持续改进
- 定期重构优化代码
- 更新依赖库版本
- 改进监控和告警
- 收集用户反馈
- 跟踪技术发展趋势

---

**文档版本**: v1.0
**维护者**: 3uyuan1ee