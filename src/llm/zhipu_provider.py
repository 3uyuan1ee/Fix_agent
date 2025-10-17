#!/usr/bin/env python3
"""
ZhipuAI LLM提供者实现
基于zai-sdk实现智谱AI大语言模型支持
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, AsyncGenerator
from ..utils.logger import get_logger
from .base import LLMProvider, LLMConfig, LLMRequest, LLMResponse, Message, MessageRole
from .exceptions import (
    LLMError, LLMTimeoutError, LLMRateLimitError,
    LLMNetworkError, LLMAuthenticationError, LLMQuotaExceededError,
    LLMModelNotFoundError, LLMTokenLimitError, LLMContentFilterError,
    LLMProviderUnavailableError
)

try:
    import zai
    from zai import ZhipuAiClient
    ZHIPU_AVAILABLE = True
except ImportError:
    ZHIPU_AVAILABLE = False
    ZhipuAiClient = None

logger = get_logger()


class ZhipuProvider(LLMProvider):
    """ZhipuAI LLM提供者"""

    def __init__(self, config: LLMConfig):
        """
        初始化ZhipuProvider

        Args:
            config: LLM配置
        """
        super().__init__(config)

        if not ZHIPU_AVAILABLE:
            raise LLMProviderUnavailableError(
                "zai-sdk is not installed. Install with: pip install zai-sdk"
            )

        # 初始化ZhipuAI客户端
        self.client = ZhipuAiClient(
            api_key=config.api_key,
            base_url=config.api_base or "https://open.bigmodel.cn/api/paas/v4/",
            timeout=config.timeout,
            max_retries=config.max_retries
        )

        # 支持的模型列表
        self.supported_models = [
            "glm-4.5",
            "glm-4.5-air",
            "glm-4",
            "glm-4-air",
            "glm-4-airx",
            "glm-4-flash",
            "glm-4v",  # 视觉模型
            "glm-3-turbo",
            "embedding-2",
            "embedding-3"
        ]

    @property
    def provider_name(self) -> str:
        """提供者名称"""
        return "zhipu"

    def validate_request(self, request: LLMRequest) -> None:
        """
        验证请求

        Args:
            request: LLM请求

        Raises:
            ValueError: 请求无效
        """
        if not request.messages:
            raise ValueError("Messages are required")

        # 验证模型是否支持
        if self.config.model not in self.supported_models:
            logger.warning(f"Model {self.config.model} may not be supported. Supported models: {self.supported_models}")

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
            # 转换消息格式
            messages = self._convert_messages(request.messages)

            # 准备请求参数
            kwargs = {
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "top_p": self.config.top_p
            }

            # 添加可选参数
            if request.tools:
                kwargs["tools"] = request.tools
            if request.tool_choice:
                kwargs["tool_choice"] = request.tool_choice

            # 发送请求
            response = self.client.chat.completions.create(**kwargs)

            # 解析响应
            result = self._parse_response(response, request.request_id, start_time)

            logger.info(f"ZhipuAI request completed: {result.usage}")
            return result

        except zai.core.APIStatusError as e:
            logger.error(f"ZhipuAI API status error: {e}")
            raise LLMError(f"API status error: {e}")
        except zai.core.APITimeoutError as e:
            logger.error(f"ZhipuAI API timeout: {e}")
            raise LLMTimeoutError(f"API timeout: {e}")
        except zai.core.APIConnectionError as e:
            logger.error(f"ZhipuAI connection error: {e}")
            raise LLMNetworkError(f"Connection error: {e}")
        except zai.core.AuthenticationError as e:
            logger.error(f"ZhipuAI authentication error: {e}")
            raise LLMAuthenticationError(f"Authentication failed: {e}")
        except zai.core.RateLimitError as e:
            logger.error(f"ZhipuAI rate limit error: {e}")
            raise LLMRateLimitError(f"Rate limit exceeded: {e}")
        except zai.core.APIError as e:
            logger.error(f"ZhipuAI API error: {e}")
            raise LLMError(f"API error: {e}")
        except Exception as e:
            logger.error(f"ZhipuAI unexpected error: {e}")
            raise LLMError(f"Unexpected error: {e}")

    async def stream_complete(self, request: LLMRequest) -> AsyncGenerator[LLMResponse, None]:
        """
        流式完成文本生成请求

        Args:
            request: LLM请求

        Yields:
            LLM响应片段
        """
        self.validate_request(request)
        start_time = time.time()

        try:
            # 转换消息格式
            messages = self._convert_messages(request.messages)

            # 准备请求参数
            kwargs = {
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "top_p": self.config.top_p,
                "stream": True
            }

            # 添加可选参数
            if request.tools:
                kwargs["tools"] = request.tools
            if request.tool_choice:
                kwargs["tool_choice"] = request.tool_choice

            # 发送流式请求
            response_stream = self.client.chat.completions.create(**kwargs)

            # 处理流式响应
            for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    result = self._parse_stream_chunk(chunk, request.request_id, start_time)
                    yield result

        except zai.core.APIStatusError as e:
            logger.error(f"ZhipuAI API status error in stream: {e}")
            raise LLMError(f"API status error: {e}")
        except zai.core.APITimeoutError as e:
            logger.error(f"ZhipuAI API timeout in stream: {e}")
            raise LLMTimeoutError(f"API timeout: {e}")
        except zai.core.APIConnectionError as e:
            logger.error(f"ZhipuAI connection error in stream: {e}")
            raise LLMNetworkError(f"Connection error: {e}")
        except zai.core.AuthenticationError as e:
            logger.error(f"ZhipuAI authentication error in stream: {e}")
            raise LLMAuthenticationError(f"Authentication failed: {e}")
        except zai.core.RateLimitError as e:
            logger.error(f"ZhipuAI rate limit error in stream: {e}")
            raise LLMRateLimitError(f"Rate limit exceeded: {e}")
        except zai.core.APIError as e:
            logger.error(f"ZhipuAI API error in stream: {e}")
            raise LLMError(f"API error: {e}")
        except Exception as e:
            logger.error(f"ZhipuAI unexpected error in stream: {e}")
            raise LLMError(f"Unexpected error: {e}")

    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """
        转换消息格式

        Args:
            messages: 原始消息列表

        Returns:
            转换后的消息列表
        """
        converted = []
        for msg in messages:
            msg_dict = {
                "role": msg.role.value,
                "content": msg.content
            }
            if msg.name:
                msg_dict["name"] = msg.name
            if msg.function_call:
                msg_dict["function_call"] = msg.function_call
            converted.append(msg_dict)
        return converted

    def _parse_response(self, response, request_id: str, start_time: float) -> LLMResponse:
        """
        解析响应

        Args:
            response: ZhipuAI响应
            request_id: 请求ID
            start_time: 开始时间

        Returns:
            LLM响应
        """
        choice = response.choices[0] if response.choices else None
        content = choice.message.content if choice and choice.message else ""

        # 解析使用情况
        usage = None
        if hasattr(response, 'usage') and response.usage:
            usage = {
                "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0),
                "completion_tokens": getattr(response.usage, 'completion_tokens', 0),
                "total_tokens": getattr(response.usage, 'total_tokens', 0)
            }

        # 解析工具调用
        tool_calls = None
        if choice and hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in choice.message.tool_calls
            ]

        return LLMResponse(
            request_id=request_id,
            provider=self.provider_name,
            model=response.model,
            content=content,
            finish_reason=choice.finish_reason if choice else None,
            usage=usage,
            response_time=time.time() - start_time,
            tool_calls=tool_calls
        )

    def _parse_stream_chunk(self, chunk, request_id: str, start_time: float) -> LLMResponse:
        """
        解析流式响应片段

        Args:
            chunk: 流式响应片段
            request_id: 请求ID
            start_time: 开始时间

        Returns:
            LLM响应片段
        """
        if not chunk.choices:
            return LLMResponse(
                request_id=request_id,
                provider=self.provider_name,
                model=self.config.model,
                content="",
                is_stream=True,
                is_complete=False
            )

        choice = chunk.choices[0]
        delta = choice.delta

        content = delta.content if hasattr(delta, 'content') and delta.content else ""
        finish_reason = choice.finish_reason if hasattr(choice, 'finish_reason') else None

        # 解析工具调用
        tool_calls = None
        if hasattr(delta, 'tool_calls') and delta.tool_calls:
            tool_calls = [
                {
                    "id": tc.id if hasattr(tc, 'id') else None,
                    "type": tc.type if hasattr(tc, 'type') else None,
                    "function": {
                        "name": tc.function.name if hasattr(tc.function, 'name') else None,
                        "arguments": tc.function.arguments if hasattr(tc.function, 'arguments') else None
                    }
                }
                for tc in delta.tool_calls
            ]

        return LLMResponse(
            request_id=request_id,
            provider=self.provider_name,
            model=chunk.model if hasattr(chunk, 'model') else self.config.model,
            content=content,
            delta=content,
            finish_reason=finish_reason,
            is_stream=True,
            is_complete=finish_reason is not None,
            response_time=time.time() - start_time,
            tool_calls=tool_calls
        )

    def get_default_config(self) -> Dict[str, Any]:
        """
        获取默认配置

        Returns:
            默认配置字典
        """
        config = super().get_default_config()
        config.update({
            "model": "glm-4.5",
            "api_base": "https://open.bigmodel.cn/api/paas/v4/",
            "max_tokens": 4000,
            "temperature": 0.7
        })
        return config

    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数量

        Args:
            text: 文本内容

        Returns:
            估算的token数量
        """
        # 对于中文，大约1.5个字符=1个token
        # 对于英文，大约4个字符=1个token
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        other_chars = len(text) - chinese_chars
        return max(1, int(chinese_chars / 1.5 + other_chars / 4))

    def estimate_cost(self, request: LLMRequest, response: LLMResponse) -> float:
        """
        估算请求成本（人民币）

        Args:
            request: 请求
            response: 响应

        Returns:
            估算成本（人民币）
        """
        # GLM-4.5 定价 (示例价格，需要根据实际价格调整)
        pricing = {
            "glm-4.5": {"input": 0.01, "output": 0.025},  # 每1000 tokens人民币价格
            "glm-4": {"input": 0.01, "output": 0.025},
            "glm-4-air": {"input": 0.005, "output": 0.0125},
            "glm-4-flash": {"input": 0.001, "output": 0.002},
            "glm-3-turbo": {"input": 0.005, "output": 0.0125}
        }

        model_pricing = pricing.get(self.config.model, {"input": 0.01, "output": 0.025})

        input_tokens = response.usage.get("prompt_tokens", 0) if response.usage else 0
        output_tokens = response.usage.get("completion_tokens", 0) if response.usage else 0

        cost = (input_tokens * model_pricing["input"] +
                output_tokens * model_pricing["output"]) / 1000

        return cost

    def get_provider_models(self) -> List[str]:
        """
        获取提供者支持的模型列表

        Returns:
            模型列表
        """
        return self.supported_models.copy()

    def supports_function_calling(self) -> bool:
        """
        是否支持函数调用

        Returns:
            是否支持函数调用
        """
        return True

    def supports_streaming(self) -> bool:
        """
        是否支持流式响应

        Returns:
            是否支持流式响应
        """
        return True

    def supports_vision(self) -> bool:
        """
        是否支持视觉理解

        Returns:
            是否支持视觉理解
        """
        return self.config.model == "glm-4v"

    def supports_embeddings(self) -> bool:
        """
        是否支持文本嵌入

        Returns:
            是否支持文本嵌入
        """
        return self.config.model.startswith("embedding")