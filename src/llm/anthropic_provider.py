"""
Anthropic API适配器
"""

import asyncio
import time
from typing import Any, AsyncGenerator, Dict, List

from ..utils.logger import get_logger
from .base import LLMProvider, LLMRequest, LLMResponse
from .exceptions import LLMError, LLMRateLimitError, LLMTimeoutError
from .http_client import HTTPClient, RetryConfig


class AnthropicProvider(LLMProvider):
    """Anthropic API提供者"""

    def __init__(self, config):
        """
        初始化Anthropic提供者

        Args:
            config: LLM配置
        """
        super().__init__(config)
        self.logger = get_logger()
        self.http_client = HTTPClient(
            RetryConfig(max_retries=config.max_retries, base_delay=config.retry_delay)
        )

    @property
    def provider_name(self) -> str:
        """提供者名称"""
        return "anthropic"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """
        完成文本生成请求

        Args:
            request: LLM请求

        Returns:
            LLM响应
        """
        self.validate_request(request)

        start_time = time.time()

        try:
            headers = self._prepare_headers()
            url = self._build_url()
            data = self._prepare_request_data(request)

            # 发送请求
            response_data = await self.http_client.request(
                method="POST",
                url=url,
                headers=headers,
                data=data,
                timeout=request.config.timeout or self.config.timeout,
            )

            # 解析响应
            response = self._parse_response(response_data)
            response.response_time = time.time() - start_time

            self.logger.debug(
                f"Anthropic request completed in {response.response_time:.2f}s"
            )
            return response

        except Exception as e:
            self.logger.error(f"Anthropic request failed: {e}")
            raise

    async def stream_complete(
        self, request: LLMRequest
    ) -> AsyncGenerator[LLMResponse, None]:
        """
        流式完成文本生成请求

        Args:
            request: LLM请求

        Yields:
            LLM响应片段
        """
        self.validate_request(request)

        try:
            headers = self._prepare_headers()
            url = self._build_url()
            data = self._prepare_request_data(request)

            # 设置流式模式
            data["stream"] = True

            start_time = time.time()
            request_id = ""

            async for chunk_data in self.http_client.stream_request(
                method="POST",
                url=url,
                headers=headers,
                data=data,
                timeout=request.config.timeout or self.config.timeout,
            ):
                response = self._parse_stream_chunk(chunk_data, request_id)
                if response.request_id:
                    request_id = response.request_id
                response.response_time = time.time() - start_time
                yield response

        except Exception as e:
            self.logger.error(f"Anthropic stream request failed: {e}")
            raise

    def validate_request(self, request: LLMRequest) -> None:
        """
        验证请求

        Args:
            request: LLM请求

        Raises:
            ValueError: 请求无效
        """
        if not request.messages:
            raise ValueError("Messages cannot be empty")

        # Anthropic对消息顺序有特殊要求
        # 第一个消息必须是system消息
        if request.messages[0].role.value != "system":
            # 如果没有system消息，添加一个默认的
            from .base import Message, MessageRole

            request.messages.insert(
                0,
                Message(
                    role=MessageRole.SYSTEM, content="You are a helpful AI assistant."
                ),
            )
            self.logger.info("Added default system message for Anthropic")

        # 验证消息格式
        for message in request.messages:
            if not message.content.strip():
                raise ValueError(f"Message content cannot be empty: {message}")

    def _prepare_headers(self) -> Dict[str, str]:
        """准备请求头"""
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "User-Agent": "AIDefectDetector/1.0",
        }

        if self.config.api_base:
            headers["Host"] = self.config.api_base.replace("https://", "").replace(
                "http://", ""
            )

        return headers

    def _build_url(self) -> str:
        """构建API URL"""
        base_url = self.config.api_base or "https://api.anthropic.com/v1"
        return f"{base_url.rstrip('/')}/messages"

    def _prepare_request_data(self, request: LLMRequest) -> Dict[str, Any]:
        """准备请求数据"""
        messages = []
        for msg in request.messages:
            message_dict = {"role": msg.role.value, "content": msg.content}
            messages.append(message_dict)

        data = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens or 1000,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "stream": request.config.stream or self.config.stream,
        }

        # Anthropic特有的参数
        if self.config.stop:
            data["stop_sequences"] = (
                self.config.stop
                if isinstance(self.config.stop, list)
                else [self.config.stop]
            )

        # 添加工具调用相关参数
        if request.tools:
            data["tools"] = request.tools
        if request.tool_choice:
            data["tool_choice"] = request.tool_choice

        # 添加自定义参数
        data.update(self.config.custom_params)

        return data

    def _parse_response(self, data: Dict[str, Any]) -> LLMResponse:
        """解析响应数据"""
        usage = data.get("usage", {})
        content = data.get("content", "")
        stop_reason = data.get("stop_reason", "")

        return LLMResponse(
            request_id=data.get("id", ""),
            provider=self.provider_name,
            model=data.get("model", self.config.model),
            content=content,
            finish_reason=stop_reason,
            usage={
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0)
                + usage.get("output_tokens", 0),
            },
            created_at=data.get("created_at", time.time()),
        )

    def _parse_stream_chunk(
        self, chunk: Dict[str, Any], request_id: str = ""
    ) -> LLMResponse:
        """解析流式响应片段"""
        if "type" not in chunk:
            return LLMResponse(
                request_id=request_id,
                provider=self.provider_name,
                model=self.config.model,
                content="",
                is_stream=True,
                is_complete=False,
            )

        if chunk["type"] == "message_start":
            return LLMResponse(
                request_id=chunk.get("message", {}).get("id", request_id),
                provider=self.provider_name,
                model=chunk.get("model", self.config.model),
                content="",
                is_stream=True,
                is_complete=False,
            )

        elif chunk["type"] == "content_block_delta":
            return LLMResponse(
                request_id=request_id,
                provider=self.provider_name,
                model=chunk.get("model", self.config.model),
                content=chunk.get("delta", {}).get("text", ""),
                delta=chunk.get("delta", {}).get("text", ""),
                is_stream=True,
                is_complete=False,
            )

        elif chunk["type"] == "message_delta":
            # 处理消息结束
            return LLMResponse(
                request_id=request_id,
                provider=self.provider_name,
                model=chunk.get("model", self.config.model),
                content=chunk.get("delta", {}).get("text", ""),
                delta=chunk.get("delta", {}).get("text", ""),
                is_stream=True,
                is_complete=True,
            )

        elif chunk["type"] == "message_stop":
            return LLMResponse(
                request_id=request_id,
                provider=self.provider_name,
                model=chunk.get("model", self.config.model),
                content="",
                finish_reason=chunk.get("stop_reason", "end_turn"),
                is_stream=True,
                is_complete=True,
            )

        return LLMResponse(
            request_id=request_id,
            provider=self.provider_name,
            model=self.config.model,
            content="",
            is_stream=True,
            is_complete=False,
        )

    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "model": "claude-3-sonnet-20240229",
            "temperature": 0.7,
            "max_tokens": 1000,
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 1.0,
            "api_base": "https://api.anthropic.com/v1",
        }

    def estimate_tokens(self, text: str) -> int:
        """
        估算token数量（针对Anthropic优化）

        Args:
            text: 文本内容

        Returns:
            估算的token数量
        """
        # Anthropic的token估算规则大致与OpenAI相似
        # 但Claude模型可能略有不同

        # 简单实现：按字符类型分别计算
        ascii_chars = 0
        chinese_chars = 0
        other_chars = 0

        for char in text:
            if ord(char) < 128:  # ASCII字符
                ascii_chars += 1
            elif "\u4e00" <= char <= "\u9fff":  # 中文字符
                chinese_chars += 1
            else:
                other_chars += 1

        # 估算tokens
        ascii_tokens = ascii_chars // 4
        chinese_tokens = chinese_chars // 1.5  # 约1.5个汉字=1token
        other_tokens = other_chars // 4

        return max(1, int(ascii_tokens + chinese_tokens + other_tokens))

    def estimate_cost(self, request: LLMRequest, response: LLMResponse) -> float:
        """
        估算Anthropic请求成本

        Args:
            request: 请求
            response: 响应

        Returns:
            估算成本（美元）
        """
        # Anthropic定价（2024年，仅供参考）
        # Claude 3 Opus: $15.0/1M input tokens, $75.0/1M output tokens
        # Claude 3 Sonnet: $3.0/1M input tokens, $15.0/1M output tokens
        # Claude 3 Haiku: $0.25/1M input tokens, $1.25/1M output tokens
        # Claude 2.1: $8.0/1M input tokens, $24.0/1M output tokens
        # Claude Instant: $0.8/1M input tokens, $2.4/1M output tokens

        pricing = {
            "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
            "claude-3-sonnet-20240229": {"input": 3.0, "output": 15.0},
            "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
            "claude-2.1": {"input": 8.0, "output": 24.0},
            "claude-2.0": {"input": 8.0, "output": 24.0},
            "claude-instant-1.2": {"input": 0.8, "output": 2.4},
        }

        model_name = response.model.lower()
        if model_name not in pricing:
            # 使用默认定价（Claude 3 Sonnet）
            model_name = "claude-3-sonnet-20240229"

        rates = pricing[model_name]
        input_price = rates["input"]
        output_price = rates["output"]

        if response.usage:
            input_tokens = response.usage.get("prompt_tokens", 0)
            output_tokens = response.usage.get("completion_tokens", 0)
        else:
            # 估算tokens
            input_tokens = sum(
                self.estimate_tokens(msg.content) for msg in request.messages
            )
            output_tokens = self.estimate_tokens(response.content)

        # 将价格从每1M tokens转换为每1K tokens
        cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
        return cost

    def get_supported_models(self) -> List[str]:
        """获取支持的模型列表"""
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2",
            "claude-instant-1.1",
        ]

    def check_model_availability(self, model: str) -> bool:
        """
        检查模型是否可用

        Args:
            model: 模型名称

        Returns:
            模型是否可用
        """
        return model in self.get_supported_models()
