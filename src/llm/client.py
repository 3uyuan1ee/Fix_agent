"""
统一的LLM客户端
提供统一的大语言模型API调用接口
"""

import asyncio
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from dataclasses import dataclass
import time

from .base import LLMProvider, LLMConfig, LLMRequest, LLMResponse, Message, MessageRole
from .exceptions import LLMError, LLMTimeoutError, LLMRateLimitError, LLMAuthenticationError, LLMQuotaExceededError
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .config import LLMConfigManager
from ..utils.logger import get_logger


@dataclass
class LLMClientConfig:
    """LLM客户端配置"""
    default_provider: str = "openai"
    fallback_providers: List[str] = None
    enable_fallback: bool = True
    max_retry_attempts: int = 3
    timeout: int = 30

    def __post_init__(self):
        if self.fallback_providers is None:
            self.fallback_providers = ["anthropic"]


class LLMClient:
    """统一的LLM客户端"""

    def __init__(self, config: Optional[Union[LLMClientConfig, Dict[str, Any]]] = None,
                 config_manager: Optional[LLMConfigManager] = None):
        """
        初始化LLM客户端

        Args:
            config: 客户端配置
            config_manager: 配置管理器
        """
        self.logger = get_logger()

        # 处理配置
        if isinstance(config, dict):
            config = LLMClientConfig(**config)
        self.config = config or LLMClientConfig()

        # 配置管理器
        self.config_manager = config_manager or LLMConfigManager()

        # 统计信息（必须在提供者初始化之前）
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "fallback_used": 0,
            "provider_usage": {}
        }

        # 初始化提供者
        self.providers: Dict[str, LLMProvider] = {}
        self._init_providers()

    def _init_providers(self):
        """初始化所有可用的提供者"""
        try:
            # 初始化OpenAI
            openai_config = self.config_manager.get_config("openai")
            self.providers["openai"] = OpenAIProvider(openai_config)
            self.stats["provider_usage"]["openai"] = 0
        except Exception as e:
            self.logger.warning(f"Failed to initialize OpenAI provider: {e}")

        try:
            # 初始化Anthropic
            anthropic_config = self.config_manager.get_config("anthropic")
            self.providers["anthropic"] = AnthropicProvider(anthropic_config)
            self.stats["provider_usage"]["anthropic"] = 0
        except Exception as e:
            self.logger.warning(f"Failed to initialize Anthropic provider: {e}")

        if not self.providers:
            raise LLMError("No LLM providers available")

    async def complete(self, request: LLMRequest,
                      provider: Optional[str] = None) -> LLMResponse:
        """
        完成文本生成请求

        Args:
            request: LLM请求
            provider: 指定的提供者，如果为None则使用默认提供者

        Returns:
            LLM响应
        """
        self.stats["total_requests"] += 1
        start_time = time.time()

        # 确定使用的提供者顺序
        if provider:
            providers_to_try = [provider]
        else:
            providers_to_try = [self.config.default_provider]
            if self.config.enable_fallback and self.config.fallback_providers:
                providers_to_try.extend(self.config.fallback_providers)

        # 过滤掉不可用的提供者
        available_providers = [p for p in providers_to_try if p in self.providers]
        if not available_providers:
            raise LLMError(f"No available providers in: {providers_to_try}")

        # 尝试每个提供者
        last_error = None
        for i, provider_name in enumerate(available_providers):
            try:
                self.logger.debug(f"Trying provider: {provider_name}")
                provider = self.providers[provider_name]

                # 发送请求
                response = await provider.complete(request)

                # 更新统计信息
                response_time = time.time() - start_time
                self.stats["successful_requests"] += 1
                self.stats["provider_usage"][provider_name] = self.stats["provider_usage"].get(provider_name, 0) + 1

                if i > 0:  # 使用了回退
                    self.stats["fallback_used"] += 1
                    self.logger.info(f"Fallback to {provider_name} succeeded after {response_time:.2f}s")

                return response

            except Exception as e:
                last_error = e
                self.logger.warning(f"Provider {provider_name} failed: {e}")

                # 如果是最后一个提供者，或者是不应该重试的错误，直接抛出
                if i == len(available_providers) - 1:
                    break
                elif isinstance(e, (LLMRateLimitError, LLMAuthenticationError, LLMQuotaExceededError)):
                    # 这些错误不应该重试其他提供者
                    raise e

        # 所有提供者都失败了
        self.stats["failed_requests"] += 1
        raise last_error or LLMError("All providers failed")

    async def stream_complete(self, request: LLMRequest,
                           provider: Optional[str] = None) -> AsyncGenerator[LLMResponse, None]:
        """
        流式完成文本生成请求

        Args:
            request: LLM请求
            provider: 指定的提供者

        Yields:
            LLM响应片段
        """
        self.stats["total_requests"] += 1

        # 确定使用的提供者
        provider_name = provider or self.config.default_provider
        if provider_name not in self.providers:
            raise LLMError(f"Provider {provider_name} not available")

        try:
            provider = self.providers[provider_name]

            # 流式响应
            async for response in provider.stream_complete(request):
                yield response

            self.stats["successful_requests"] += 1
            self.stats["provider_usage"][provider_name] = self.stats["provider_usage"].get(provider_name, 0) + 1

        except Exception as e:
            self.stats["failed_requests"] += 1
            self.logger.error(f"Stream completion failed with provider {provider_name}: {e}")
            raise

    def create_request(self, messages: List[Union[str, Message]],
                      **kwargs) -> LLMRequest:
        """
        创建LLM请求

        Args:
            messages: 消息列表，可以是字符串或Message对象
            **kwargs: 其他请求参数

        Returns:
            LLM请求对象
        """
        # 转换消息格式
        processed_messages = []
        for msg in messages:
            if isinstance(msg, str):
                processed_messages.append(Message(role=MessageRole.USER, content=msg))
            else:
                processed_messages.append(msg)

        # 获取默认配置
        default_config = self.config_manager.get_config(self.config.default_provider)

        # 合并配置
        config_dict = default_config.to_dict()
        config_dict.update(kwargs)
        config = LLMConfig.from_dict(config_dict)

        return LLMRequest(messages=processed_messages, config=config)

    def get_provider_names(self) -> List[str]:
        """获取可用的提供者名称列表"""
        return list(self.providers.keys())

    def get_stats(self) -> Dict[str, Any]:
        """获取客户端统计信息"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_requests"] / self.stats["total_requests"]
                if self.stats["total_requests"] > 0 else 0
            ),
            "fallback_rate": (
                self.stats["fallback_used"] / self.stats["total_requests"]
                if self.stats["total_requests"] > 0 else 0
            )
        }

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "fallback_used": 0,
            "provider_usage": {}
        }

    async def test_connection(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        测试与提供者的连接

        Args:
            provider: 要测试的提供者，如果为None则测试所有提供者

        Returns:
            测试结果
        """
        results = {}

        providers_to_test = [provider] if provider else self.get_provider_names()

        for provider_name in providers_to_test:
            if provider_name not in self.providers:
                results[provider_name] = {
                    "status": "unavailable",
                    "error": "Provider not initialized"
                }
                continue

            try:
                test_request = self.create_request(
                    ["Hello, this is a connection test."],
                    max_tokens=10,
                    temperature=0.1
                )

                start_time = time.time()
                response = await self.complete(test_request, provider=provider_name)
                response_time = time.time() - start_time

                results[provider_name] = {
                    "status": "success",
                    "response_time": response_time,
                    "model": response.model,
                    "provider": response.provider
                }

            except Exception as e:
                results[provider_name] = {
                    "status": "failed",
                    "error": str(e)
                }

        return results