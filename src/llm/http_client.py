"""
HTTP客户端模块，提供请求处理、重试和异常管理
"""

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Callable, Dict, Optional, Union

import aiohttp

from ..utils.logger import get_logger
from .exceptions import (
    LLMAuthenticationError,
    LLMError,
    LLMNetworkError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMTimeoutError,
)


@dataclass
class RetryConfig:
    """重试配置"""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


class HTTPClient:
    """HTTP客户端，提供重试机制和异常处理"""

    def __init__(self, retry_config: Optional[RetryConfig] = None):
        """
        初始化HTTP客户端

        Args:
            retry_config: 重试配置
        """
        self.retry_config = retry_config or RetryConfig()
        self.logger = get_logger()
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    async def _ensure_session(self) -> None:
        """确保会话存在"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=300, connect=30)
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def close(self) -> None:
        """关闭会话"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[str, Dict[str, Any]]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        发送HTTP请求

        Args:
            method: HTTP方法
            url: 请求URL
            headers: 请求头
            data: 请求数据
            params: 查询参数
            timeout: 超时时间
            **kwargs: 其他参数

        Returns:
            响应数据

        Raises:
            LLMError: 请求失败
        """
        await self._ensure_session()

        # 准备请求数据
        if isinstance(data, dict):
            data = json.dumps(data)

        # 设置超时
        request_timeout = aiohttp.ClientTimeout(total=timeout)

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                async with self.session.request(
                    method,
                    url,
                    headers=headers,
                    data=data,
                    params=params,
                    timeout=request_timeout,
                    **kwargs,
                ) as response:
                    # 检查响应状态
                    await self._check_response_status(response)

                    # 解析响应数据
                    response_data = await self._parse_response(response)
                    return response_data

            except (
                LLMError,
                LLMAuthenticationError,
                LLMRateLimitError,
                LLMQuotaExceededError,
            ) as e:
                # LLM相关异常不需要重试，直接抛出
                self.logger.warning(
                    f"LLM error (attempt {attempt + 1}/{self.retry_config.max_retries + 1}): {e}"
                )
                raise e

            except asyncio.TimeoutError as e:
                self.logger.warning(
                    f"Request timeout (attempt {attempt + 1}/{self.retry_config.max_retries + 1}): {e}"
                )
                if attempt == self.retry_config.max_retries:
                    raise LLMTimeoutError(
                        f"Request timeout after {self.retry_config.max_retries} retries"
                    )

            except aiohttp.ClientError as e:
                error_msg = f"Request failed (attempt {attempt + 1}/{self.retry_config.max_retries + 1}): {e}"
                self.logger.warning(error_msg)

                # 检查是否需要特殊处理
                if isinstance(e, aiohttp.ClientResponseError):
                    await self._handle_client_response_error(e)

                if attempt == self.retry_config.max_retries:
                    raise LLMNetworkError(
                        f"Request failed after {self.retry_config.max_retries} retries: {e}"
                    )

            except Exception as e:
                self.logger.warning(
                    f"Unexpected error (attempt {attempt + 1}/{self.retry_config.max_retries + 1}): {e}"
                )
                if attempt == self.retry_config.max_retries:
                    raise LLMError(
                        f"Unexpected error after {self.retry_config.max_retries} retries: {e}"
                    )

            # 等待重试
            if attempt < self.retry_config.max_retries:
                delay = self._calculate_retry_delay(attempt)
                await asyncio.sleep(delay)

        # 这里不应该到达
        raise LLMError("Request failed unexpectedly")

    async def stream_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[str, Dict[str, Any]]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        发送流式HTTP请求

        Args:
            method: HTTP方法
            url: 请求URL
            headers: 请求头
            data: 请求数据
            params: 查询参数
            timeout: 超时时间
            **kwargs: 其他参数

        Yields:
            响应数据片段

        Raises:
            LLMError: 请求失败
        """
        await self._ensure_session()

        # 准备请求数据
        if isinstance(data, dict):
            data = json.dumps(data)

        # 设置超时
        request_timeout = aiohttp.ClientTimeout(total=timeout)

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                async with self.session.request(
                    method,
                    url,
                    headers=headers,
                    data=data,
                    params=params,
                    timeout=request_timeout,
                    **kwargs,
                ) as response:
                    # 检查响应状态
                    await self._check_response_status(response)

                    # 流式读取响应
                    async for chunk in self._read_stream_response(response):
                        yield chunk

                    return  # 成功完成，退出重试循环

            except (
                LLMError,
                LLMAuthenticationError,
                LLMRateLimitError,
                LLMQuotaExceededError,
            ) as e:
                # LLM相关异常不需要重试，直接抛出
                self.logger.warning(
                    f"LLM stream error (attempt {attempt + 1}/{self.retry_config.max_retries + 1}): {e}"
                )
                raise e

            except asyncio.TimeoutError as e:
                self.logger.warning(
                    f"Stream request timeout (attempt {attempt + 1}/{self.retry_config.max_retries + 1}): {e}"
                )
                if attempt == self.retry_config.max_retries:
                    raise LLMTimeoutError(
                        f"Stream request timeout after {self.retry_config.max_retries} retries"
                    )

            except aiohttp.ClientError as e:
                error_msg = f"Stream request failed (attempt {attempt + 1}/{self.retry_config.max_retries + 1}): {e}"
                self.logger.warning(error_msg)

                if isinstance(e, aiohttp.ClientResponseError):
                    await self._handle_client_response_error(e)

                if attempt == self.retry_config.max_retries:
                    raise LLMNetworkError(
                        f"Stream request failed after {self.retry_config.max_retries} retries: {e}"
                    )

            except Exception as e:
                self.logger.warning(
                    f"Unexpected stream error (attempt {attempt + 1}/{self.retry_config.max_retries + 1}): {e}"
                )
                if attempt == self.retry_config.max_retries:
                    raise LLMError(
                        f"Unexpected stream error after {self.retry_config.max_retries} retries: {e}"
                    )

            # 等待重试
            if attempt < self.retry_config.max_retries:
                delay = self._calculate_retry_delay(attempt)
                await asyncio.sleep(delay)

        # 这里不应该到达
        raise LLMError("Stream request failed unexpectedly")

    async def _check_response_status(self, response: aiohttp.ClientResponse) -> None:
        """检查响应状态"""
        if response.status >= 400:
            error_data = None
            try:
                error_data = await response.json()
            except:
                try:
                    error_data = await response.text()
                except:
                    error_data = response.reason

            if response.status == 401:
                raise LLMAuthenticationError(
                    "Authentication failed", error_code=str(response.status)
                )
            elif response.status == 429:
                retry_after = None
                if "Retry-After" in response.headers:
                    try:
                        retry_after = int(response.headers["Retry-After"])
                    except ValueError:
                        pass
                raise LLMRateLimitError(
                    "Rate limit exceeded",
                    error_code=str(response.status),
                    retry_after=retry_after,
                )
            elif response.status == 402:
                raise LLMQuotaExceededError(
                    "Quota exceeded", error_code=str(response.status)
                )
            else:
                raise LLMNetworkError(
                    f"HTTP {response.status}: {response.reason}",
                    error_code=str(response.status),
                )

    async def _handle_client_response_error(
        self, error: aiohttp.ClientResponseError
    ) -> None:
        """处理客户端响应错误"""
        # 可以根据需要实现特定的错误处理逻辑
        pass

    async def _parse_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """解析响应数据"""
        content_type = response.headers.get("Content-Type", "").lower()

        if "application/json" in content_type:
            try:
                return await response.json()
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON response: {e}")
                return {"raw_text": await response.text()}
        else:
            return {"raw_text": await response.text()}

    async def _read_stream_response(
        self, response: aiohttp.ClientResponse
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """读取流式响应"""
        content_type = response.headers.get("Content-Type", "").lower()

        if "text/event-stream" in content_type:
            # Server-Sent Events格式
            async for line in response.content:
                if line:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]  # 移除 "data: " 前缀
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            yield data
                        except json.JSONDecodeError:
                            # 可能是部分数据，继续处理
                            continue

        else:
            # 其他流式格式
            async for chunk in response.content:
                if chunk:
                    chunk_str = chunk.decode("utf-8")
                    try:
                        data = json.loads(chunk_str)
                        yield data
                    except json.JSONDecodeError:
                        # 返回原始文本
                        yield {"raw_text": chunk_str}

    def _calculate_retry_delay(self, attempt: int) -> float:
        """计算重试延迟"""
        delay = self.retry_config.base_delay * (
            self.retry_config.exponential_base**attempt
        )
        delay = min(delay, self.retry_config.max_delay)

        if self.retry_config.jitter:
            # 添加随机抖动，避免雷群效应
            import random

            delay *= 0.5 + random.random() * 0.5

        return delay


class RetryableMixin:
    """重试混入类，提供重试装饰器"""

    @staticmethod
    def retry_async(
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        exceptions: tuple = (Exception,),
    ):
        """
        重试装饰器

        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟时间
            max_delay: 最大延迟时间
            exponential_base: 指数退避底数
            jitter: 是否添加随机抖动
            exceptions: 需要重试的异常类型
        """

        def decorator(func):
            async def wrapper(*args, **kwargs):
                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        if attempt == max_retries:
                            raise

                        delay = base_delay * (exponential_base**attempt)
                        delay = min(delay, max_delay)

                        if jitter:
                            import random

                            delay *= 0.5 + random.random() * 0.5

                        await asyncio.sleep(delay)

                # 这里不应该到达
                raise

            return wrapper

        return decorator
