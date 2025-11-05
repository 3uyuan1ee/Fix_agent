"""
OpenAI API适配器
"""

import asyncio
import time
from typing import Any, AsyncGenerator, Dict, List

from ..utils.logger import get_logger
from .base import LLMProvider, LLMRequest, LLMResponse
from .exceptions import LLMError, LLMRateLimitError, LLMTimeoutError
from .http_client import HTTPClient, RetryConfig


class OpenAIProvider(LLMProvider):
    """OpenAI API提供者"""

    def __init__(self, config):
        """
        初始化OpenAI提供者

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
        return "openai"

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
                f"OpenAI request completed in {response.response_time:.2f}s"
            )
            return response

        except Exception as e:
            self.logger.error(f"OpenAI request failed: {e}")
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
            self.logger.error(f"OpenAI stream request failed: {e}")
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

        # 验证消息格式
        for message in request.messages:
            if not message.content.strip():
                raise ValueError(f"Message content cannot be empty: {message}")

        # 验证工具调用
        if request.tools and not any(
            msg.role.value == "system" for msg in request.messages
        ):
            # 工具调用通常需要系统消息
            self.logger.warning("Tool calls usually require a system message")

    def _prepare_headers(self) -> Dict[str, str]:
        """准备请求头"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
            "User-Agent": "AIDefectDetector/1.0",
        }

        if self.config.organization:
            headers["OpenAI-Organization"] = self.config.organization

        if self.config.api_base:
            headers["Host"] = self.config.api_base.replace("https://", "").replace(
                "http://", ""
            )

        return headers

    def _build_url(self) -> str:
        """构建API URL"""
        base_url = self.config.api_base or "https://api.openai.com/v1"
        return f"{base_url.rstrip('/')}/chat/completions"

    def _prepare_request_data(self, request: LLMRequest) -> Dict[str, Any]:
        """准备请求数据"""
        messages = []
        for msg in request.messages:
            message_dict = {"role": msg.role.value, "content": msg.content}
            if msg.name:
                message_dict["name"] = msg.name
            if msg.function_call:
                message_dict["function_call"] = msg.function_call
            messages.append(message_dict)

        data = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "frequency_penalty": self.config.frequency_penalty,
            "presence_penalty": self.config.presence_penalty,
            "stream": request.config.stream or self.config.stream,
        }

        # 添加可选参数
        if self.config.max_tokens:
            data["max_tokens"] = self.config.max_tokens
        if self.config.stop:
            data["stop"] = self.config.stop
        if self.config.logprobs:
            data["logprobs"] = self.config.logprobs
        if self.config.echo:
            data["echo"] = self.config.echo

        # 添加工具调用相关参数
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

    def _parse_response(self, data: Dict[str, Any]) -> LLMResponse:
        """解析响应数据"""
        usage = data.get("usage", {})
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})

        return LLMResponse(
            request_id=data.get("id", ""),
            provider=self.provider_name,
            model=data.get("model", self.config.model),
            content=message.get("content", ""),
            finish_reason=choice.get("finish_reason"),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            created_at=data.get("created", time.time()),
            function_call=message.get("function_call"),
            tool_calls=message.get("tool_calls"),
        )

    def _parse_stream_chunk(
        self, chunk: Dict[str, Any], request_id: str = ""
    ) -> LLMResponse:
        """解析流式响应片段"""
        if "choices" not in chunk or not chunk["choices"]:
            return LLMResponse(
                request_id=request_id,
                provider=self.provider_name,
                model=self.config.model,
                content="",
                is_stream=True,
                is_complete=False,
            )

        choice = chunk["choices"][0]
        delta = choice.get("delta", {})

        return LLMResponse(
            request_id=chunk.get("id", request_id),
            provider=self.provider_name,
            model=chunk.get("model", self.config.model),
            content=delta.get("content", ""),
            delta=delta.get("content"),
            finish_reason=choice.get("finish_reason"),
            is_stream=True,
            is_complete=choice.get("finish_reason") is not None,
            function_call=delta.get("function_call"),
            tool_calls=delta.get("tool_calls"),
        )

    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 1000,
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 1.0,
            "api_base": "https://api.openai.com/v1",
        }

    def estimate_tokens(self, text: str) -> int:
        """
        估算token数量（针对OpenAI优化）

        Args:
            text: 文本内容

        Returns:
            估算的token数量
        """
        # OpenAI的token估算大致规则
        # 英文：1 token ≈ 4 个字符
        # 中文：1 token ≈ 1.5-2 个汉字
        # 代码：1 token ≈ 3-4 个字符

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
        估算OpenAI请求成本

        Args:
            request: 请求
            response: 响应

        Returns:
            估算成本（美元）
        """
        # OpenAI定价（2024年，仅供参考）
        # GPT-4: $0.03/1K input tokens, $0.06/1K output tokens
        # GPT-4-Turbo: $0.001/1K input tokens, $0.002/1K output tokens
        # GPT-3.5-Turbo: $0.0005/1K input tokens, $0.0015/1K output tokens

        pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-32k": {"input": 0.06, "output": 0.12},
            "gpt-4-turbo": {"input": 0.001, "output": 0.002},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
            "text-davinci-003": {"input": 0.02, "output": 0.02},
            "text-curie-001": {"input": 0.002, "output": 0.002},
        }

        model_name = response.model.lower()
        if model_name not in pricing:
            # 使用默认定价（GPT-3.5-Turbo）
            model_name = "gpt-3.5-turbo"

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

        cost = (input_tokens * input_price + output_tokens * output_price) / 1000
        return cost

    def get_supported_models(self) -> List[str]:
        """获取支持的模型列表"""
        return [
            "gpt-4",
            "gpt-4-32k",
            "gpt-4-turbo",
            "gpt-4-turbo-preview",
            "gpt-4-vision-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            "gpt-3.5-turbo-1106",
            "gpt-3.5-turbo-instruct",
            "text-davinci-003",
            "text-curie-001",
            "text-babbage-001",
            "text-ada-001",
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
