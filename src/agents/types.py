"""
代码缺陷检测系统核心类型定义

本模块定义了系统中使用的所有数据类型、接口和协议，
确保类型安全和接口一致性。
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union


class MessageType(Enum):
    """消息类型枚举"""

    TASK_REQUEST = "task_request"
    ANALYSIS_RESULT = "analysis_result"
    FIX_GENERATED = "fix_generated"
    VALIDATION_RESULT = "validation_result"
    COORDINATION = "coordination"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    COMPLETION = "completion"


class Priority(Enum):
    """任务优先级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DefectSeverity(Enum):
    """缺陷严重程度"""

    INFO = "info"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"
    BLOCKER = "blocker"


class TaskStatus(Enum):
    """任务状态"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CodeLocation:
    """代码位置信息"""

    file_path: str
    line_number: int
    column_number: Optional[int] = None
    end_line: Optional[int] = None
    end_column: Optional[int] = None


@dataclass
class CodeDefect:
    """代码缺陷信息"""

    id: str
    severity: DefectSeverity
    type: str
    message: str
    location: CodeLocation
    suggestion: Optional[str] = None
    rule_id: Optional[str] = None
    confidence: float = 0.0
    context: Optional[str] = None


@dataclass
class FixSuggestion:
    """修复建议"""

    defect_id: str
    description: str
    code_changes: List[Dict[str, Any]]
    impact_analysis: str
    confidence: float = 0.0
    automated_fix: bool = False


@dataclass
class TestResult:
    """测试结果"""

    test_name: str
    status: Literal["passed", "failed", "skipped", "error"]
    execution_time: float
    error_message: Optional[str] = None
    coverage_percentage: Optional[float] = None


class BaseMessage(TypedDict):
    """基础消息类型"""

    id: str
    type: MessageType
    timestamp: str
    sender: str
    recipient: Optional[str]
    priority: Priority


class TaskRequestMessage(BaseMessage):
    """任务请求消息"""

    project_path: str
    target_files: Optional[List[str]]
    analysis_types: List[str]
    requirements: Dict[str, Any]


class AnalysisResultMessage(BaseMessage):
    """分析结果消息"""

    task_id: str
    defects: List[CodeDefect]
    analysis_summary: Dict[str, Any]
    execution_time: float


class FixGeneratedMessage(BaseMessage):
    """修复生成消息"""

    task_id: str
    fixes: List[FixSuggestion]
    modified_files: List[str]
    fix_summary: Dict[str, Any]


class ValidationResultMessage(BaseMessage):
    """验证结果消息"""

    task_id: str
    test_results: List[TestResult]
    validation_summary: Dict[str, Any]
    regression_detected: bool


class CoordinationMessage(BaseMessage):
    """协调消息"""

    workflow_state: str
    current_phase: str
    next_actions: List[str]
    context: Dict[str, Any]


class ErrorMessage(BaseMessage):
    """错误消息"""

    error_code: str
    error_message: str
    stack_trace: Optional[str]
    recovery_suggestions: List[str]


# 联合类型定义
SystemMessage = Union[
    TaskRequestMessage,
    AnalysisResultMessage,
    FixGeneratedMessage,
    ValidationResultMessage,
    CoordinationMessage,
    ErrorMessage,
]


class WorkflowState(TypedDict):
    """工作流状态"""

    session_id: str
    current_phase: Literal["analysis", "fix_generation", "validation", "completed"]
    task_status: Dict[str, TaskStatus]
    message_history: List[BaseMessage]
    context: Dict[str, Any]
    created_at: str
    updated_at: str


class AgentConfig(TypedDict):
    """代理配置"""

    name: str
    type: Literal["coordinator", "analysis", "fix_generation", "validation"]
    model: str
    tools: List[str]
    middleware: List[str]
    capabilities: List[str]
    max_retries: int
    timeout: int


class SystemConfig(TypedDict):
    """系统配置"""

    agents: Dict[str, AgentConfig]
    middleware: Dict[str, Any]
    tools: Dict[str, Any]
    workflow: Dict[str, Any]
    logging: Dict[str, Any]
    storage: Dict[str, Any]


# 工具接口定义
class ToolProtocol(TypedDict):
    """工具协议"""

    name: str
    description: str
    parameters: Dict[str, Any]
    return_type: str


# 中间件接口定义
class MiddlewareConfig(TypedDict):
    """中间件配置"""

    name: str
    enabled: bool
    config: Dict[str, Any]


# 消息处理协议
class MessageHandler(TypedDict):
    """消息处理器"""

    handler_name: str
    message_types: List[MessageType]
    handler_func: str
    async_handler: bool


# 事件类型定义
class EventType(Enum):
    """事件类型"""

    WORKFLOW_STARTED = "workflow_started"
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    DEFECT_FOUND = "defect_found"
    FIX_APPLIED = "fix_applied"
    VALIDATION_COMPLETED = "validation_completed"
    ERROR_OCCURRED = "error_occurred"
    WORKFLOW_COMPLETED = "workflow_completed"


class SystemEvent(TypedDict):
    """系统事件"""

    id: str
    type: EventType
    timestamp: str
    source: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
