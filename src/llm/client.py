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
from .zhipu_provider import ZhipuProvider
from .mock_provider import MockLLMProvider
from .config import LLMConfigManager
from ..utils.logger import get_logger


@dataclass
class LLMClientConfig:
    """LLM客户端配置"""
    default_provider: str = "zhipu"  # 默认使用智谱AI (国内稳定)
    fallback_providers: List[str] = None
    enable_fallback: bool = True
    max_retry_attempts: int = 3
    timeout: int = 30

    def __post_init__(self):
        if self.fallback_providers is None:
            self.fallback_providers = ["openai", "anthropic", "mock"]  # 回退到其他provider


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

        # 初始化全局并发管理器
        concurrency_config = self.config_manager.get_concurrency_config()
        if concurrency_config:
            from .concurrency_manager import get_global_concurrency_manager
            self.concurrency_manager = get_global_concurrency_manager(concurrency_config.max_concurrent_requests)
        else:
            from .concurrency_manager import get_global_concurrency_manager
            self.concurrency_manager = get_global_concurrency_manager(5)

    def _init_providers(self):
        """初始化所有可用的提供者"""
        # 初始化智谱AI
        try:
            zhipu_config = self.config_manager.get_config("zhipu")
            if zhipu_config:
                self.providers["zhipu"] = ZhipuProvider(zhipu_config)
                self.stats["provider_usage"]["zhipu"] = 0
                self.logger.info("ZhipuAI provider initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize ZhipuAI provider: {e}")

        try:
            # 初始化OpenAI
            openai_config = self.config_manager.get_config("openai")
            if openai_config:
                self.providers["openai"] = OpenAIProvider(openai_config)
                self.stats["provider_usage"]["openai"] = 0
                self.logger.info("OpenAI provider initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize OpenAI provider: {e}")

        try:
            # 初始化Anthropic
            anthropic_config = self.config_manager.get_config("anthropic")
            if anthropic_config:
                self.providers["anthropic"] = AnthropicProvider(anthropic_config)
                self.stats["provider_usage"]["anthropic"] = 0
                self.logger.info("Anthropic provider initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Anthropic provider: {e}")

        # 初始化Mock Provider（用于测试）
        try:
            mock_config = self.config_manager.get_config("mock")
            if mock_config:
                self.providers["mock"] = MockLLMProvider(mock_config)
                self.stats["provider_usage"]["mock"] = 0
                self.logger.info("Mock provider initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Mock provider: {e}")

        if not self.providers:
            raise LLMError("No LLM providers available")

    async def complete(self, request: LLMRequest,
                      provider: Optional[str] = None) -> LLMResponse:
        """
        完成文本生成请求（带全局并发控制）

        Args:
            request: LLM请求
            provider: 指定的提供者，如果为None则使用默认提供者

        Returns:
            LLM响应
        """
        # 使用全局并发管理器执行请求
        return await self.concurrency_manager.execute_request(
            self._complete_with_providers, request, provider
        )

    async def _complete_with_providers(self, request: LLMRequest,
                                     provider: Optional[str] = None) -> LLMResponse:
        """
        内部方法：使用指定提供者完成请求

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
            # 如果指定了provider，只尝试该provider和其fallback
            providers_to_try = [provider]
            # 如果指定的provider失败，允许使用fallback providers
            if self.config.enable_fallback and self.config.fallback_providers:
                providers_to_try.extend(self.config.fallback_providers)
        else:
            # 如果没有指定provider，使用默认provider和fallback
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
                provider_obj = self.providers[provider_name]

                # 发送请求
                response = await provider_obj.complete(request)

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
            elif isinstance(msg, dict):
                # 处理字典格式 {"role": "user", "content": "..."}
                role = msg.get("role", "user")
                content = msg.get("content", "")

                # 转换role字符串到MessageRole枚举
                if role in ["user", "User"]:
                    msg_role = MessageRole.USER
                elif role in ["assistant", "Assistant"]:
                    msg_role = MessageRole.ASSISTANT
                elif role in ["system", "System"]:
                    msg_role = MessageRole.SYSTEM
                else:
                    msg_role = MessageRole.USER

                processed_messages.append(Message(role=msg_role, content=content))
            else:
                # 假设是Message对象
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

    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        同步聊天补全接口（兼容智谱AI和OpenAI格式）

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            **kwargs: 其他参数 (temperature, max_tokens, model等)

        Returns:
            Dict[str, Any]: 响应结果
            {
                "success": bool,
                "content": str,
                "error_message": str,
                "usage": dict,
                "model": str
            }
        """
        try:
            # 创建请求
            request = self.create_request(messages, **kwargs)

            # 异步执行
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，使用新的线程执行
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self.complete(request))
                        response = future.result()
                else:
                    # 如果没有运行的事件循环，直接运行
                    response = loop.run_until_complete(self.complete(request))
            except RuntimeError:
                # 创建新的事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                response = loop.run_until_complete(self.complete(request))

            # LLMResponse对象总是成功的，除非有异常
            # 构建兼容格式的响应
            result = {
                "success": True,
                "content": response.content,
                "model": response.model,
                "finish_reason": response.finish_reason
            }

            # 添加使用情况
            if response.usage:
                result["usage"] = response.usage
            else:
                result["usage"] = {}

            return result

        except Exception as e:
            self.logger.error(f"Chat completion failed: {e}")
            return {
                "success": False,
                "error_message": str(e)
            }

    async def chat_completion_async(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        异步聊天补全接口

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            **kwargs: 其他参数 (temperature, max_tokens, model, provider等)

        Returns:
            Dict[str, Any]: 响应结果
            {
                "success": bool,
                "content": str,
                "error_message": str,
                "usage": dict,
                "model": str
            }
        """
        try:
            # 提取provider参数
            provider = kwargs.pop('provider', None)

            # 创建请求
            request = self.create_request(messages, **kwargs)

            # 异步执行，传递provider参数
            response = await self.complete(request, provider=provider)

            # 构建兼容格式的响应
            result = {
                "success": True,
                "content": response.content,
                "model": response.model,
                "finish_reason": response.finish_reason
            }

            # 添加使用情况
            if response.usage:
                result["usage"] = response.usage
            else:
                result["usage"] = {}

            return result

        except Exception as e:
            self.logger.error(f"Async chat completion failed: {e}")
            return {
                "success": False,
                "error_message": str(e)
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