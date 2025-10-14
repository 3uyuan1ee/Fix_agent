"""
测试HTTP客户端
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
import aiohttp
from aiohttp import ClientResponseError, ClientError, ServerTimeoutError

from src.llm.http_client import HTTPClient, RetryConfig, RetryableMixin
from src.llm.exceptions import (
    LLMTimeoutError, LLMRateLimitError, LLMNetworkError,
    LLMAuthenticationError, LLMQuotaExceededError, LLMError
)


class TestRetryConfig:
    """测试重试配置"""

    def test_default_retry_config(self):
        """测试默认重试配置"""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_custom_retry_config(self):
        """测试自定义重试配置"""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False
        )
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is False


class TestHTTPClient:
    """测试HTTP客户端"""

    @pytest.fixture
    def retry_config(self):
        """重试配置fixture"""
        return RetryConfig(max_retries=2, base_delay=0.1, jitter=False)

    @pytest.fixture
    def http_client(self, retry_config):
        """HTTP客户端fixture"""
        return HTTPClient(retry_config)

    @pytest.mark.asyncio
    async def test_context_manager(self, http_client):
        """测试异步上下文管理器"""
        async with http_client as client:
            assert client.session is not None
            assert not client.session.closed
        assert http_client.session is None or http_client.session.closed

    @pytest.mark.asyncio
    async def test_ensure_session(self, http_client):
        """测试确保会话存在"""
        assert http_client.session is None
        await http_client._ensure_session()
        assert http_client.session is not None
        assert not http_client.session.closed

    @pytest.mark.asyncio
    async def test_close(self, http_client):
        """测试关闭会话"""
        await http_client._ensure_session()
        session = http_client.session
        await http_client.close()
        assert session.closed

    @pytest.mark.asyncio
    async def test_successful_request(self, http_client):
        """测试成功的请求"""
        mock_response_data = {"id": "test", "content": "Hello"}

        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_response.headers = {'Content-Type': 'application/json'}

            mock_request.return_value.__aenter__.return_value = mock_response

            async with http_client:
                result = await http_client.request(
                    method="POST",
                    url="https://api.example.com/chat",
                    data={"message": "Hello"}
                )

                assert result == mock_response_data
                mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_with_dict_data(self, http_client):
        """测试使用字典数据的请求"""
        mock_response_data = {"result": "success"}

        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_response.headers = {'Content-Type': 'application/json'}

            mock_request.return_value.__aenter__.return_value = mock_response

            async with http_client:
                result = await http_client.request(
                    method="POST",
                    url="https://api.example.com/chat",
                    data={"message": "Hello"}
                )

                # 验证数据被序列化为JSON
                call_args = mock_request.call_args
                assert isinstance(call_args[1]['data'], str)
                assert json.loads(call_args[1]['data']) == {"message": "Hello"}

    @pytest.mark.asyncio
    async def test_request_timeout_error(self, http_client):
        """测试请求超时错误"""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_request.side_effect = asyncio.TimeoutError("Request timeout")

            async with http_client:
                with pytest.raises(LLMTimeoutError, match="Request timeout after"):
                    await http_client.request(
                        method="POST",
                        url="https://api.example.com/chat",
                        data={"message": "Hello"}
                    )

    @pytest.mark.asyncio
    async def test_request_client_error(self, http_client):
        """测试客户端错误"""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_request.side_effect = ClientError("Connection failed")

            async with http_client:
                with pytest.raises(LLMNetworkError, match="Request failed after"):
                    await http_client.request(
                        method="POST",
                        url="https://api.example.com/chat",
                        data={"message": "Hello"}
                    )

    @pytest.mark.asyncio
    async def test_request_authentication_error(self, http_client):
        """测试认证错误"""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_response.json = AsyncMock(return_value={"error": "Unauthorized"})
            mock_response.headers = {}

            mock_request.return_value.__aenter__.return_value = mock_response

            async with http_client:
                with pytest.raises(LLMAuthenticationError, match="Authentication failed"):
                    await http_client.request(
                        method="POST",
                        url="https://api.example.com/chat",
                        data={"message": "Hello"}
                    )

    @pytest.mark.asyncio
    async def test_request_rate_limit_error(self, http_client):
        """测试速率限制错误"""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 429
            mock_response.json = AsyncMock(return_value={"error": "Rate limit"})
            mock_response.headers = {"Retry-After": "60"}

            mock_request.return_value.__aenter__.return_value = mock_response

            async with http_client:
                with pytest.raises(LLMRateLimitError) as exc_info:
                    await http_client.request(
                        method="POST",
                        url="https://api.example.com/chat",
                        data={"message": "Hello"}
                    )

                assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_request_quota_exceeded_error(self, http_client):
        """测试配额超限错误"""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 402
            mock_response.json = AsyncMock(return_value={"error": "Quota exceeded"})
            mock_response.headers = {}

            mock_request.return_value.__aenter__.return_value = mock_response

            async with http_client:
                with pytest.raises(LLMQuotaExceededError, match="Quota exceeded"):
                    await http_client.request(
                        method="POST",
                        url="https://api.example.com/chat",
                        data={"message": "Hello"}
                    )

    @pytest.mark.asyncio
    async def test_successful_stream_request(self, http_client):
        """测试成功的流式请求"""
        stream_data = [
            b'data: {"delta": "Hello"}\n\n',
            b'data: {"delta": " world"}\n\n',
            b'data: [DONE]\n\n'
        ]

        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {'Content-Type': 'text/event-stream'}

            # 创建正确的异步迭代器模拟
            async def mock_content_iter():
                for data in stream_data:
                    yield data

            mock_response.content = mock_content_iter()

            mock_request.return_value.__aenter__.return_value = mock_response

            async with http_client:
                chunks = []
                async for chunk in http_client.stream_request(
                    method="POST",
                    url="https://api.example.com/chat",
                    data={"message": "Hello", "stream": True}
                ):
                    chunks.append(chunk)

                assert len(chunks) == 2  # [DONE]被过滤掉
                assert chunks[0]["delta"] == "Hello"
                assert chunks[1]["delta"] == " world"

    @pytest.mark.asyncio
    async def test_stream_request_with_json_content(self, http_client):
        """测试JSON格式的流式请求"""
        stream_data = [
            b'{"content": "Hello"}',
            b'{"content": " world"}'
        ]

        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {'Content-Type': 'application/json'}

            # 创建正确的异步迭代器模拟
            async def mock_content_iter():
                for data in stream_data:
                    yield data

            mock_response.content = mock_content_iter()

            mock_request.return_value.__aenter__.return_value = mock_response

            async with http_client:
                chunks = []
                async for chunk in http_client.stream_request(
                    method="POST",
                    url="https://api.example.com/chat",
                    data={"message": "Hello", "stream": True}
                ):
                    chunks.append(chunk)

                assert len(chunks) == 2
                assert chunks[0]["content"] == "Hello"
                assert chunks[1]["content"] == " world"

    @pytest.mark.asyncio
    async def test_calculate_retry_delay_without_jitter(self, http_client):
        """测试不使用抖动的重试延迟计算"""
        delay = http_client._calculate_retry_delay(1)  # 第一次重试
        expected_delay = 0.1 * (2.0 ** 1)  # base_delay * exponential_base^attempt
        assert delay == expected_delay

    @pytest.mark.asyncio
    async def test_calculate_retry_delay_with_jitter(self):
        """测试使用抖动的重试延迟计算"""
        config = RetryConfig(max_retries=2, base_delay=0.1, jitter=True)
        client = HTTPClient(config)

        # 测试多次调用，延迟应该在预期范围内变化
        delays = []
        for _ in range(10):
            delay = client._calculate_retry_delay(1)
            delays.append(delay)

        # 所有延迟应该在50%-100%的预期延迟之间
        expected_delay = 0.1 * (2.0 ** 1)
        for delay in delays:
            assert expected_delay * 0.5 <= delay <= expected_delay

    @pytest.mark.asyncio
    async def test_max_delay_cap(self, http_client):
        """测试最大延迟限制"""
        # 使用大数值尝试
        delay = http_client._calculate_retry_delay(10)
        assert delay <= http_client.retry_config.max_delay

    @pytest.mark.asyncio
    async def test_response_parsing_json_error(self, http_client):
        """测试响应JSON解析错误"""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
            mock_response.text = AsyncMock(return_value="Plain text response")
            mock_response.headers = {'Content-Type': 'application/json'}

            mock_request.return_value.__aenter__.return_value = mock_response

            async with http_client:
                result = await http_client.request(
                    method="POST",
                    url="https://api.example.com/chat",
                    data={"message": "Hello"}
                )

                assert result == {"raw_text": "Plain text response"}

    @pytest.mark.asyncio
    async def test_response_parsing_plain_text(self, http_client):
        """测试纯文本响应解析"""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="Plain text response")
            mock_response.headers = {'Content-Type': 'text/plain'}

            mock_request.return_value.__aenter__.return_value = mock_response

            async with http_client:
                result = await http_client.request(
                    method="POST",
                    url="https://api.example.com/chat",
                    data={"message": "Hello"}
                )

                assert result == {"raw_text": "Plain text response"}


class TestRetryableMixin:
    """测试重试混入类"""

    @pytest.mark.asyncio
    async def test_retry_decorator_success(self):
        """测试重试装饰器成功情况"""
        call_count = 0

        @RetryableMixin.retry_async(max_retries=2, base_delay=0.01)
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "success"

        result = await test_function()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_decorator_max_retries(self):
        """测试重试装饰器达到最大重试次数"""
        @RetryableMixin.retry_async(max_retries=2, base_delay=0.01)
        async def failing_function():
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            await failing_function()

    @pytest.mark.asyncio
    async def test_retry_decorator_custom_exceptions(self):
        """测试重试装饰器自定义异常类型"""
        call_count = 0

        @RetryableMixin.retry_async(
            max_retries=2,
            base_delay=0.01,
            exceptions=(ValueError,)
        )
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry me")
            return "success"

        result = await test_function()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_decorator_wrong_exception(self):
        """测试重试装饰器不匹配的异常类型"""
        @RetryableMixin.retry_async(
            max_retries=2,
            base_delay=0.01,
            exceptions=(ValueError,)
        )
        async def test_function():
            raise TypeError("Don't retry me")

        with pytest.raises(TypeError, match="Don't retry me"):
            await test_function()