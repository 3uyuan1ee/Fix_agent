"""
LLM接口基础抽象类和数据模型
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import uuid
import json
import time


class MessageRole(Enum):
    """消息角色枚举"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


@dataclass
class Message:
    """消息数据类"""
    role: MessageRole
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMConfig:
    """LLM配置数据类"""
    provider: str
    model: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    organization: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: Optional[Union[str, List[str]]] = None
    stream: bool = False
    logprobs: Optional[int] = None
    echo: bool = False
    # 自定义配置
    custom_params: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """验证配置"""
        if not self.provider:
            raise ValueError("Provider is required")
        if not self.model:
            raise ValueError("Model is required")
        if self.temperature < 0 or self.temperature > 2:
            raise ValueError("Temperature must be between 0 and 2")
        if self.top_p < 0 or self.top_p > 1:
            raise ValueError("Top_p must be between 0 and 1")
        if self.frequency_penalty < -2 or self.frequency_penalty > 2:
            raise ValueError("Frequency penalty must be between -2 and 2")
        if self.presence_penalty < -2 or self.presence_penalty > 2:
            raise ValueError("Presence penalty must be between -2 and 2")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("Max retries must be non-negative")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "provider": self.provider,
            "model": self.model,
            "api_key": self.api_key,
            "api_base": self.api_base,
            "api_version": self.api_version,
            "organization": self.organization,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "stop": self.stop,
            "stream": self.stream,
            "logprobs": self.logprobs,
            "echo": self.echo,
            "custom_params": self.custom_params
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMConfig":
        """从字典创建配置"""
        return cls(**data)


@dataclass
class LLMRequest:
    """LLM请求数据类"""
    messages: List[Message]
    config: LLMConfig
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    functions: Optional[List[Dict[str, Any]]] = None
    function_call: Optional[Union[str, Dict[str, Any]]] = None
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: MessageRole, content: str, **kwargs) -> None:
        """添加消息"""
        message = Message(role=role, content=content, **kwargs)
        self.messages.append(message)

    def get_last_message(self) -> Optional[Message]:
        """获取最后一条消息"""
        return self.messages[-1] if self.messages else None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "name": msg.name,
                    "function_call": msg.function_call,
                    "metadata": msg.metadata
                }
                for msg in self.messages
            ],
            "config": self.config.to_dict(),
            "tools": self.tools,
            "tool_choice": self.tool_choice,
            "functions": self.functions,
            "function_call": self.function_call,
            "request_id": self.request_id,
            "metadata": self.metadata
        }
        return {k: v for k, v in result.items() if v is not None}


@dataclass
class LLMResponse:
    """LLM响应数据类"""
    request_id: str
    provider: str
    model: str
    content: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    created_at: float = field(default_factory=time.time)
    response_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    # 流式响应相关
    delta: Optional[str] = None
    is_stream: bool = False
    is_complete: bool = True
    # 工具调用相关
    tool_calls: Optional[List[Dict[str, Any]]] = None
    function_call: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "request_id": self.request_id,
            "provider": self.provider,
            "model": self.model,
            "content": self.content,
            "finish_reason": self.finish_reason,
            "usage": self.usage,
            "created_at": self.created_at,
            "response_time": self.response_time,
            "metadata": self.metadata,
            "delta": self.delta,
            "is_stream": self.is_stream,
            "is_complete": self.is_complete,
            "tool_calls": self.tool_calls,
            "function_call": self.function_call
        }
        return {k: v for k, v in result.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMResponse":
        """从字典创建响应"""
        return cls(**data)


class LLMProvider(ABC):
    """LLM提供者抽象基类"""

    def __init__(self, config: LLMConfig):
        """
        初始化LLM提供者

        Args:
            config: LLM配置
        """
        self.config = config
        self.config.validate()

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供者名称"""
        pass

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """
        完成文本生成请求

        Args:
            request: LLM请求

        Returns:
            LLM响应
        """
        pass

    @abstractmethod
    async def stream_complete(self, request: LLMRequest):
        """
        流式完成文本生成请求

        Args:
            request: LLM请求

        Yields:
            LLM响应片段
        """
        pass

    @abstractmethod
    def validate_request(self, request: LLMRequest) -> None:
        """
        验证请求

        Args:
            request: LLM请求

        Raises:
            ValueError: 请求无效
        """
        pass

    def get_default_config(self) -> Dict[str, Any]:
        """
        获取默认配置

        Returns:
            默认配置字典
        """
        return {
            "temperature": 0.7,
            "max_tokens": 1000,
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 1.0
        }

    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数量（简单实现）

        Args:
            text: 文本内容

        Returns:
            估算的token数量
        """
        # 简单的token估算：大约4个字符=1个token
        return max(1, len(text) // 4)

    def estimate_cost(self, request: LLMRequest, response: LLMResponse) -> float:
        """
        估算请求成本（简单实现）

        Args:
            request: 请求
            response: 响应

        Returns:
            估算成本（美元）
        """
        # 默认成本计算（需要子类重写）
        input_tokens = sum(self.estimate_tokens(msg.content) for msg in request.messages)
        output_tokens = self.estimate_tokens(response.content) if response.content else 0

        # 默认价格（每1000 tokens）
        input_price = 0.001
        output_price = 0.002

        return (input_tokens * input_price + output_tokens * output_price) / 1000

    def prepare_headers(self) -> Dict[str, str]:
        """
        准备请求头

        Returns:
            请求头字典
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"AIDefectDetector/1.0 ({self.provider_name})"
        }

        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        if self.config.organization:
            headers["OpenAI-Organization"] = self.config.organization

        return headers

    def prepare_request_data(self, request: LLMRequest) -> Dict[str, Any]:
        """
        准备请求数据

        Args:
            request: LLM请求

        Returns:
            请求数据字典
        """
        data = {
            "model": self.config.model,
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content
                }
                for msg in request.messages
            ],
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "frequency_penalty": self.config.frequency_penalty,
            "presence_penalty": self.config.presence_penalty,
            "stream": request.config.stream or self.config.stream
        }

        if self.config.max_tokens:
            data["max_tokens"] = self.config.max_tokens

        if self.config.stop:
            data["stop"] = self.config.stop

        if self.config.logprobs:
            data["logprobs"] = self.config.logprobs

        if request.tools:
            data["tools"] = request.tools

        if request.tool_choice:
            data["tool_choice"] = request.tool_choice

        if request.functions:
            data["functions"] = request.functions

        if request.function_call:
            data["function_call"] = request.function_call

        # 添加自定义参数
        data.update(self.config.custom_params)

        return data

    def parse_response_data(self, data: Dict[str, Any]) -> LLMResponse:
        """
        解析响应数据

        Args:
            data: 响应数据

        Returns:
            LLM响应
        """
        usage = data.get("usage", {})

        return LLMResponse(
            request_id=data.get("id", ""),
            provider=self.provider_name,
            model=data.get("model", self.config.model),
            content=data.get("choices", [{}])[0].get("message", {}).get("content", ""),
            finish_reason=data.get("choices", [{}])[0].get("finish_reason"),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            },
            created_at=data.get("created", time.time()),
            tool_calls=data.get("choices", [{}])[0].get("message", {}).get("tool_calls"),
            function_call=data.get("choices", [{}])[0].get("message", {}).get("function_call")
        )

    def parse_stream_chunk(self, chunk: Dict[str, Any]) -> LLMResponse:
        """
        解析流式响应片段

        Args:
            chunk: 响应片段

        Returns:
            LLM响应片段
        """
        if "choices" not in chunk or not chunk["choices"]:
            return LLMResponse(
                request_id="",
                provider=self.provider_name,
                model=self.config.model,
                content="",
                is_stream=True,
                is_complete=False
            )

        choice = chunk["choices"][0]
        delta = choice.get("delta", {})

        return LLMResponse(
            request_id=chunk.get("id", ""),
            provider=self.provider_name,
            model=chunk.get("model", self.config.model),
            content=delta.get("content", ""),
            delta=delta.get("content"),
            finish_reason=choice.get("finish_reason"),
            is_stream=True,
            is_complete=choice.get("finish_reason") is not None,
            tool_calls=delta.get("tool_calls"),
            function_call=delta.get("function_call")
        )