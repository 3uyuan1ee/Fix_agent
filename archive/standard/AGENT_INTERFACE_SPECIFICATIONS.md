# Fix_agent- 接口规范文档

## 文档目的
本文档定义了Fix_agent开发系统中所有核心组件的统一接口规范，确保各模块间的一致性和兼容性。

---

## 核心数据类型定义

### 基础枚举类型
```python
from enum import Enum

class AgentStatus(Enum):
    """Agent状态枚举"""
    INITIALIZING = "initializing"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"
    TERMINATING = "terminating"

class MessageType(Enum):
    """消息类型枚举"""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    ERROR_MESSAGE = "error_message"
    COORDINATION = "coordination"
    HEARTBEAT = "heartbeat"
    SHUTDOWN = "shutdown"

class DataSource(Enum):
    """数据源类型枚举"""
    FILE_SYSTEM = "file_system"
    CODE_REPOSITORY = "code_repository"
    USER_INPUT = "user_input"
    EXTERNAL_API = "external_api"
    DATABASE = "database"
    SENSOR = "sensor"

class DecisionType(Enum):
    """决策类型枚举"""
    PROCEED = "proceed"
    WAIT = "wait"
    TERMINATE = "terminate"
    ESCALATE = "escalate"
    RETRY = "retry"
    ALTERNATIVE = "alternative"

class ToolCategory(Enum):
    """工具分类枚举"""
    PERCEPTION = "perception"
    DECISION = "decision"
    EXECUTION = "execution"
    UTILITY = "utility"
```

### 基础数据结构
```python
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import uuid

@dataclass
class Message:
    """消息数据结构"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str
    receiver_id: str
    message_type: MessageType
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 5  # 1-10, 10为最高优先级
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Task:
    """任务数据结构"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    priority: int = 5
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    assigned_to: Optional[str] = None
    deadline: Optional[datetime] = None

@dataclass
class AgentConfig:
    """Agent配置数据类"""
    agent_id: str
    name: str
    agent_type: str
    max_concurrent_tasks: int = 5
    heartbeat_interval: float = 30.0
    timeout: float = 60.0
    auto_restart: bool = False
    capabilities: List[str] = field(default_factory=list)
    custom_settings: Dict[str, Any] = field(default_factory=dict)
```

---

## 核心接口定义

### 1. Agent基础接口
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class IAgent(ABC):
    """Agent基础接口"""

    @abstractmethod
    async def start(self) -> bool:
        """启动Agent"""
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """停止Agent"""
        pass

    @abstractmethod
    def get_status(self) -> AgentStatus:
        """获取Agent状态"""
        pass

    @abstractmethod
    async def process_task(self, task: Task) -> Dict[str, Any]:
        """处理任务"""
        pass

    @abstractmethod
    async def send_message(self, receiver_id: str, message: Message) -> bool:
        """发送消息"""
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """获取Agent能力列表"""
        pass

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """获取运行指标"""
        pass
```

### 2. 感知模块接口
```python
@dataclass
class CollectedData:
    """收集的数据结构"""
    data_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: DataSource
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    quality_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EnvironmentState:
    """环境状态数据结构"""
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    environment_variables: Dict[str, Any] = field(default_factory=dict)
    active_context: Dict[str, Any] = field(default_factory=dict)
    available_resources: List[str] = field(default_factory=list)

class IPerceptionModule:
    """感知模块接口"""

    @abstractmethod
    async def perceive_environment(self) -> EnvironmentState:
        """感知环境状态"""
        pass

    @abstractmethod
    async def collect_data(self, source: DataSource, query: Dict[str, Any]) -> CollectedData:
        """收集数据"""
        pass

    @abstractmethod
    async def analyze_context(self, data: CollectedData) -> Dict[str, Any]:
        """分析上下文"""
        pass

    @abstractmethod
    async def update_perception(self, new_data: CollectedData) -> None:
        """更新感知状态"""
        pass
```

### 3. 决策模块接口
```python
@dataclass
class Decision:
    """决策结果"""
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_type: DecisionType
    strategy: str
    rationale: str
    expected_outcome: str
    confidence_score: float = 0.0
    execution_priority: int = 5
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ExecutionPlan:
    """执行计划"""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    timeline: Dict[str, Any] = field(default_factory=dict)
    success_criteria: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

class IDecisionModule:
    """决策模块接口"""

    @abstractmethod
    async def analyze_situation(self, perception_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析情况"""
        pass

    @abstractmethod
    async def make_decision(self, analysis: Dict[str, Any], context: Dict[str, Any]) -> Decision:
        """做出决策"""
        pass

    @abstractmethod
    async def plan_execution(self, decision: Decision, resources: Dict[str, Any]) -> ExecutionPlan:
        """制定执行计划"""
        pass

    @abstractmethod
    async def evaluate_confidence(self, decision: Decision, analysis: Dict[str, Any]) -> float:
        """评估置信度"""
        pass
```

### 4. 执行模块接口
```python
@dataclass
class ActionResult:
    """行动结果"""
    action_id: str
    status: str  # success, failed, partial
    result_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ExecutionResult:
    """执行结果"""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str
    overall_status: str  # success, failed, partial, timeout
    action_results: List[ActionResult] = field(default_factory=list)
    final_output: Dict[str, Any] = field(default_factory=dict)
    total_execution_time: float = 0.0
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

class IExecutionModule:
    """执行模块接口"""

    @abstractmethod
    async def execute_plan(self, plan: ExecutionPlan) -> ExecutionResult:
        """执行计划"""
        pass

    @abstractmethod
    async def coordinate_actions(self, actions: List[Dict[str, Any]]) -> List[ActionResult]:
        """协调行动"""
        pass

    @abstractmethod
    async def validate_outcome(self, result: ExecutionResult, expected_criteria: List[str]) -> bool:
        """验证结果"""
        pass

    @abstractmethod
    async def handle_failure(self, failure_info: Dict[str, Any]) -> Dict[str, Any]:
        """处理失败"""
        pass
```

### 5. 消息通信接口
```python
class IMessageHandler:
    """消息处理器接口"""

    @abstractmethod
    async def handle_message(self, message: Message) -> Optional[Message]:
        """处理消息"""
        pass

    @abstractmethod
    async def register_handler(self, message_type: MessageType, handler: callable) -> bool:
        """注册消息处理器"""
        pass

    @abstractmethod
    def get_handler_statistics(self) -> Dict[str, Any]:
        """获取处理统计"""
        pass

class IMessageRouter:
    """消息路由器接口"""

    @abstractmethod
    async def route_message(self, message: Message) -> bool:
        """路由消息"""
        pass

    @abstractmethod
    async def register_agent(self, agent_id: str, endpoint: str) -> bool:
        """注册Agent端点"""
        pass

    @abstractmethod
    async def unregister_agent(self, agent_id: str) -> bool:
        """注销Agent端点"""
        pass

    @abstractmethod
    def get_routing_table(self) -> Dict[str, str]:
        """获取路由表"""
        pass
```

### 6. 工具系统接口
```python
@dataclass
class ToolResult:
    """工具执行结果"""
    tool_name: str
    success: bool
    result_data: Any = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class ITool:
    """工具基础接口"""

    @abstractmethod
    def get_name(self) -> str:
        """获取工具名称"""
        pass

    @abstractmethod
    def get_category(self) -> ToolCategory:
        """获取工具分类"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """获取工具描述"""
        pass

    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """执行工具"""
        pass

    @abstractmethod
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """验证参数"""
        pass

class IToolRegistry:
    """工具注册表接口"""

    @abstractmethod
    async def register_tool(self, tool: ITool) -> bool:
        """注册工具"""
        pass

    @abstractmethod
    async def unregister_tool(self, tool_name: str) -> bool:
        """注销工具"""
        pass

    @abstractmethod
    def get_tool(self, tool_name: str) -> Optional[ITool]:
        """获取工具"""
        pass

    @abstractmethod
    def list_tools_by_category(self, category: ToolCategory) -> List[ITool]:
        """按分类列出工具"""
        pass

    @abstractmethod
    def search_tools(self, query: str) -> List[ITool]:
        """搜索工具"""
        pass
```

### 7. LLM集成接口
```python
@dataclass
class LLMRequest:
    """LLM请求数据结构"""
    prompt: str
    context: Optional[Dict[str, Any]] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stop_sequences: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LLMResponse:
    """LLM响应数据结构"""
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: Optional[str] = None
    response_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class ILLMProvider:
    """LLM提供商接口"""

    @abstractmethod
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """生成响应"""
        pass

    @abstractmethod
    async def generate_streaming_response(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """生成流式响应"""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        pass

    @abstractmethod
    def validate_request(self, request: LLMRequest) -> bool:
        """验证请求"""
        pass

class ILLMManager:
    """LLM管理器接口"""

    @abstractmethod
    async def add_provider(self, name: str, provider: ILLMProvider) -> bool:
        """添加提供商"""
        pass

    @abstractmethod
    def get_provider(self, name: str) -> Optional[ILLMProvider]:
        """获取提供商"""
        pass

    @abstractmethod
    async def set_default_provider(self, name: str) -> bool:
        """设置默认提供商"""
        pass

    @abstractmethod
    async def generate_with_fallback(self, request: LLMRequest) -> LLMResponse:
        """带回退机制的生成"""
        pass
```

### 8. 工作流引擎接口
```python
@dataclass
class WorkflowState:
    """工作流状态"""
    workflow_id: str
    current_state: str
    context: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

class IWorkflowEngine:
    """工作流引擎接口"""

    @abstractmethod
    async def start_workflow(self, workflow_def: Dict[str, Any], initial_context: Dict[str, Any]) -> str:
        """启动工作流"""
        pass

    @abstractmethod
    async def execute_step(self, workflow_id: str, step_name: str) -> Dict[str, Any]:
        """执行步骤"""
        pass

    @abstractmethod
    def get_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """获取工作流状态"""
        pass

    @abstractmethod
    async def pause_workflow(self, workflow_id: str) -> bool:
        """暂停工作流"""
        pass

    @abstractmethod
    async def resume_workflow(self, workflow_id: str) -> bool:
        """恢复工作流"""
        pass

    @abstractmethod
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """取消工作流"""
        pass
```

### 9. 上下文管理接口
```python
@dataclass
class SessionContext:
    """会话上下文"""
    session_id: str
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

class IContextManager:
    """上下文管理器接口"""

    @abstractmethod
    async def create_session(self, user_id: str, project_id: Optional[str] = None) -> str:
        """创建会话"""
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        """获取会话"""
        pass

    @abstractmethod
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """更新会话"""
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        pass

    @abstractmethod
    async def get_project_context(self, project_id: str) -> Dict[str, Any]:
        """获取项目上下文"""
        pass

    @abstractmethod
    async def update_project_context(self, project_id: str, context: Dict[str, Any]) -> bool:
        """更新项目上下文"""
        pass
```

### 10. 配置管理接口
```python
class IConfigManager:
    """配置管理器接口"""

    @abstractmethod
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        pass

    @abstractmethod
    def set_config(self, key: str, value: Any) -> None:
        """设置配置值"""
        pass

    @abstractmethod
    async def load_config(self, file_path: str) -> bool:
        """加载配置文件"""
        pass

    @abstractmethod
    async def save_config(self, file_path: str) -> bool:
        """保存配置文件"""
        pass

    @abstractmethod
    def reload_config(self) -> bool:
        """重新加载配置"""
        pass
```

---

## 通用约束和规范

### 异步操作规范
1. 所有I/O操作必须使用async/await
2. 方法签名必须包含异步标记：`async def`
3. 返回类型必须明确标注

### 错误处理规范
1. 所有接口方法应抛出具体异常类型
2. 使用自定义异常类进行错误分类
3. 提供详细的错误信息和上下文

### 日志记录规范
1. 所有关键操作必须记录日志
2. 使用统一的日志格式和级别
3. 包含必要的上下文信息

### 性能要求
1. 所有接口方法应设置合理的超时时间
2. 对于长时间运行的操作应提供进度回调
3. 支持取消操作机制

### 安全要求
1. 所有接口应进行权限验证
2. 敏感数据应进行加密处理
3. 支持审计日志记录

---

## 实现指南

### 命名约定
- 接口类以`I`开头（如IAgent）
- 数据类使用描述性名称
- 方法名使用动词开头的小驼峰命名
- 常量使用大写字母和下划线

### 版本控制
- 所有接口应包含版本信息
- 向后兼容性原则
- 废弃接口的过渡期管理

### 测试要求
- 所有接口必须有对应的单元测试
- 测试覆盖率不低于90%
- 包含集成测试和性能测试

---

**文档版本**: v1.0
