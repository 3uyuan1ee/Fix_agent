"""
测试LLM提供者实现
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.llm.base import LLMConfig, LLMRequest, Message, MessageRole
from src.llm.openai_provider import OpenAIProvider
from src.llm.anthropic_provider import AnthropicProvider
from src.llm.exceptions import (
    LLMTimeoutError, LLMRateLimitError, LLMAuthenticationError,
    LLMNetworkError, LLMError
)


class TestOpenAIProvider:
    """测试OpenAI提供者"""

    @pytest.fixture
    def openai_config(self):
        """OpenAI配置fixture"""
        return LLMConfig(
            provider="openai",
            model="gpt-3.5-turbo",
            api_key="test-openai-key",
            temperature=0.7,
            max_tokens=1000
        )

    @pytest.fixture
    def openai_provider(self, openai_config):
        """OpenAI提供者fixture"""
        return OpenAIProvider(openai_config)

    @pytest.fixture
    def sample_request(self, openai_config):
        """示例请求fixture"""
        messages = [
            Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
            Message(role=MessageRole.USER, content="Hello, how are you?")
        ]
        return LLMRequest(messages=messages, config=openai_config)

    def test_provider_name(self, openai_provider):
        """测试提供者名称"""
        assert openai_provider.provider_name == "openai"

    def test_validate_request_success(self, openai_provider, sample_request):
        """测试请求验证成功"""
        # 不应该抛出异常
        openai_provider.validate_request(sample_request)

    def test_validate_request_empty_messages(self, openai_provider):
        """测试验证空消息列表"""
        empty_request = LLMRequest(messages=[], config=openai_provider.config)
        with pytest.raises(ValueError, match="Messages cannot be empty"):
            openai_provider.validate_request(empty_request)

    def test_validate_request_empty_content(self, openai_provider):
        """测试验证空消息内容"""
        messages = [Message(role=MessageRole.USER, content="   ")]
        request = LLMRequest(messages=messages, config=openai_provider.config)
        with pytest.raises(ValueError, match="Message content cannot be empty"):
            openai_provider.validate_request(request)

    def test_validate_request_tools_without_system(self, openai_provider):
        """测试验证工具调用没有系统消息"""
        messages = [Message(role=MessageRole.USER, content="Help me")]
        request = LLMRequest(
            messages=messages,
            config=openai_provider.config,
            tools=[{"type": "function", "function": {"name": "test"}}]
        )

        # 应该记录警告但不抛出异常
        openai_provider.validate_request(request)

    def test_prepare_headers(self, openai_provider):
        """测试准备请求头"""
        headers = openai_provider._prepare_headers()
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-openai-key"
        assert "User-Agent" in headers

    def test_prepare_headers_with_organization(self, openai_config):
        """测试包含组织的请求头准备"""
        openai_config.organization = "test-org"
        provider = OpenAIProvider(openai_config)

        headers = provider._prepare_headers()
        assert "OpenAI-Organization" in headers
        assert headers["OpenAI-Organization"] == "test-org"

    def test_build_url(self, openai_provider):
        """测试构建API URL"""
        url = openai_provider._build_url()
        assert url == "https://api.openai.com/v1/chat/completions"

    def test_build_url_custom_base(self, openai_config):
        """测试自定义API基础URL"""
        openai_config.api_base = "https://custom.api.com/v2"
        provider = OpenAIProvider(openai_config)

        url = provider._build_url()
        assert url == "https://custom.api.com/v2/chat/completions"

    def test_prepare_request_data(self, openai_provider, sample_request):
        """测试准备请求数据"""
        data = openai_provider._prepare_request_data(sample_request)

        assert data["model"] == "gpt-3.5-turbo"
        assert "messages" in data
        assert len(data["messages"]) == 2
        assert data["temperature"] == 0.7
        assert data["max_tokens"] == 1000
        assert data["top_p"] == 1.0
        assert data["frequency_penalty"] == 0.0
        assert data["presence_penalty"] == 0.0

    def test_prepare_request_data_with_tools(self, openai_provider):
        """测试准备包含工具的请求数据"""
        tools = [{"type": "function", "function": {"name": "test"}}]
        messages = [Message(role=MessageRole.USER, content="Help me")]
        request = LLMRequest(
            messages=messages,
            config=openai_provider.config,
            tools=tools,
            tool_choice="auto"
        )

        data = openai_provider._prepare_request_data(request)
        assert "tools" in data
        assert data["tools"] == tools
        assert "tool_choice" in data
        assert data["tool_choice"] == "auto"

    def test_parse_response(self, openai_provider):
        """测试解析响应"""
        response_data = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "gpt-3.5-turbo-0301",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! I'm doing well, thank you for asking."
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 9,
                "completion_tokens": 12,
                "total_tokens": 21
            }
        }

        response = openai_provider._parse_response(response_data)

        assert response.request_id == "chatcmpl-test"
        assert response.provider == "openai"
        assert response.model == "gpt-3.5-turbo-0301"
        assert response.content == "Hello! I'm doing well, thank you for asking."
        assert response.finish_reason == "stop"
        assert response.usage["prompt_tokens"] == 9
        assert response.usage["completion_tokens"] == 12
        assert response.usage["total_tokens"] == 21

    def test_parse_stream_chunk(self, openai_provider):
        """测试解析流式响应片段"""
        chunk_data = {
            "id": "chatcmpl-test",
            "object": "chat.completion.chunk",
            "created": 1677652288,
            "model": "gpt-3.5-turbo-0301",
            "choices": [{
                "index": 0,
                "delta": {
                    "content": "Hello"
                },
                "finish_reason": None
            }]
        }

        response = openai_provider._parse_stream_chunk(chunk_data)

        assert response.request_id == "chatcmpl-test"
        assert response.provider == "openai"
        assert response.model == "gpt-3.5-turbo-0301"
        assert response.content == "Hello"
        assert response.delta == "Hello"
        assert response.is_stream is True
        assert response.is_complete is False

    def test_parse_stream_chunk_complete(self, openai_provider):
        """测试解析完成的流式响应片段"""
        chunk_data = {
            "id": "chatcmpl-test",
            "object": "chat.completion.chunk",
            "created": 1677652288,
            "model": "gpt-3.5-turbo-0301",
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }

        response = openai_provider._parse_stream_chunk(chunk_data)

        assert response.finish_reason == "stop"
        assert response.is_complete is True

    @pytest.mark.asyncio
    async def test_complete_success(self, openai_provider, sample_request):
        """测试成功完成请求"""
        mock_response_data = {
            "id": "test-id",
            "model": "gpt-3.5-turbo",
            "choices": [{
                "message": {"content": "Test response"},
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        }

        with patch.object(openai_provider.http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response_data

            response = await openai_provider.complete(sample_request)

            assert response.content == "Test response"
            assert response.provider == "openai"
            assert response.finish_reason == "stop"
            assert response.usage["total_tokens"] == 15
            assert response.response_time is not None

    @pytest.mark.asyncio
    async def test_complete_failure(self, openai_provider, sample_request):
        """测试请求失败"""
        with patch.object(openai_provider.http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = LLMNetworkError("Network error")

            with pytest.raises(LLMNetworkError, match="Network error"):
                await openai_provider.complete(sample_request)

    @pytest.mark.asyncio
    async def test_stream_complete_success(self, openai_provider, sample_request):
        """测试成功流式完成请求"""
        chunks = [
            {
                "id": "chunk-1",
                "model": "gpt-3.5-turbo",
                "choices": [{
                    "delta": {"content": "Hello"},
                    "finish_reason": None
                }]
            },
            {
                "id": "chunk-2",
                "model": "gpt-3.5-turbo",
                "choices": [{
                    "delta": {"content": " world!"},
                    "finish_reason": "stop"
                }]
            }
        ]

        async def mock_stream_request(*args, **kwargs):
            for chunk in chunks:
                yield chunk

        with patch.object(openai_provider.http_client, 'stream_request') as mock_stream:
            mock_stream.return_value = mock_stream_request()

            responses = []
            async for response in openai_provider.stream_complete(sample_request):
                responses.append(response)

            assert len(responses) == 2
            assert responses[0].content == "Hello"
            assert responses[1].content == " world!"
            assert responses[1].is_complete is True

    def test_estimate_tokens(self, openai_provider):
        """测试token估算"""
        # ASCII文本
        ascii_text = "Hello, world!"
        tokens = openai_provider.estimate_tokens(ascii_text)
        assert tokens > 0

        # 中文文本
        chinese_text = "你好，世界！"
        tokens = openai_provider.estimate_tokens(chinese_text)
        assert tokens > 0

        # 混合文本
        mixed_text = "Hello 你好 world 世界!"
        tokens = openai_provider.estimate_tokens(mixed_text)
        assert tokens > 0

    def test_estimate_cost(self, openai_provider, sample_request):
        """测试成本估算"""
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_response.model = "gpt-3.5-turbo"
        mock_response.usage = {
            "prompt_tokens": 10,
            "completion_tokens": 5
        }

        cost = openai_provider.estimate_cost(sample_request, mock_response)
        assert isinstance(cost, float)
        assert cost > 0

    def test_estimate_cost_without_usage(self, openai_provider, sample_request):
        """测试没有使用信息的成本估算"""
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_response.model = "gpt-3.5-turbo"
        mock_response.usage = None

        cost = openai_provider.estimate_cost(sample_request, mock_response)
        assert isinstance(cost, float)
        assert cost >= 0

    def test_get_supported_models(self, openai_provider):
        """测试获取支持的模型列表"""
        models = openai_provider.get_supported_models()
        assert isinstance(models, list)
        assert len(models) > 0
        assert "gpt-4" in models
        assert "gpt-3.5-turbo" in models

    def test_check_model_availability(self, openai_provider):
        """测试检查模型可用性"""
        assert openai_provider.check_model_availability("gpt-4") is True
        assert openai_provider.check_model_availability("gpt-3.5-turbo") is True
        assert openai_provider.check_model_availability("unknown-model") is False


class TestAnthropicProvider:
    """测试Anthropic提供者"""

    @pytest.fixture
    def anthropic_config(self):
        """Anthropic配置fixture"""
        return LLMConfig(
            provider="anthropic",
            model="claude-3-sonnet-20240229",
            api_key="test-anthropic-key",
            temperature=0.5,
            max_tokens=2000
        )

    @pytest.fixture
    def anthropic_provider(self, anthropic_config):
        """Anthropic提供者fixture"""
        return AnthropicProvider(anthropic_config)

    @pytest.fixture
    def sample_request(self, anthropic_config):
        """示例请求fixture"""
        messages = [
            Message(role=MessageRole.USER, content="Hello, how are you?")
        ]
        return LLMRequest(messages=messages, config=anthropic_config)

    def test_provider_name(self, anthropic_provider):
        """测试提供者名称"""
        assert anthropic_provider.provider_name == "anthropic"

    def test_validate_request_adds_system_message(self, anthropic_provider):
        """测试验证请求时添加系统消息"""
        messages = [Message(role=MessageRole.USER, content="Hello")]
        request = LLMRequest(messages=messages, config=anthropic_provider.config)

        anthropic_provider.validate_request(request)

        # 应该添加系统消息
        assert len(request.messages) == 2
        assert request.messages[0].role == MessageRole.SYSTEM
        assert request.messages[0].content == "You are a helpful AI assistant."
        assert request.messages[1].role == MessageRole.USER

    def test_validate_request_preserves_existing_system(self, anthropic_provider):
        """测试验证请求时保留现有系统消息"""
        messages = [
            Message(role=MessageRole.SYSTEM, content="Custom system message"),
            Message(role=MessageRole.USER, content="Hello")
        ]
        request = LLMRequest(messages=messages, config=anthropic_provider.config)

        anthropic_provider.validate_request(request)

        # 应该保留原有系统消息
        assert len(request.messages) == 2
        assert request.messages[0].role == MessageRole.SYSTEM
        assert request.messages[0].content == "Custom system message"

    def test_prepare_headers(self, anthropic_provider):
        """测试准备请求头"""
        headers = anthropic_provider._prepare_headers()
        assert "Content-Type" in headers
        assert "x-api-key" in headers
        assert headers["x-api-key"] == "test-anthropic-key"
        assert "anthropic-version" in headers
        assert headers["anthropic-version"] == "2023-06-01"

    def test_build_url(self, anthropic_provider):
        """测试构建API URL"""
        url = anthropic_provider._build_url()
        assert url == "https://api.anthropic.com/v1/messages"

    def test_prepare_request_data(self, anthropic_provider, sample_request):
        """测试准备请求数据"""
        # 先添加系统消息（Anthropic要求）
        anthropic_provider.validate_request(sample_request)

        data = anthropic_provider._prepare_request_data(sample_request)

        assert data["model"] == "claude-3-sonnet-20240229"
        assert "messages" in data
        assert len(data["messages"]) == 2  # 系统 + 用户
        assert data["temperature"] == 0.5
        assert data["max_tokens"] == 2000

    def test_parse_response(self, anthropic_provider):
        """测试解析响应"""
        response_data = {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "content": [{
                "type": "text",
                "text": "Hello! I'm doing well, thank you."
            }],
            "model": "claude-3-sonnet-20240229",
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {
                "input_tokens": 10,
                "output_tokens": 25
            }
        }

        response = anthropic_provider._parse_response(response_data)

        assert response.request_id == "msg_test"
        assert response.provider == "anthropic"
        assert response.model == "claude-3-sonnet-20240229"
        assert response.content == [{"type": "text", "text": "Hello! I'm doing well, thank you."}]
        assert response.finish_reason == "end_turn"
        assert response.usage["prompt_tokens"] == 10
        assert response.usage["completion_tokens"] == 25

    def test_parse_stream_chunk_message_start(self, anthropic_provider):
        """测试解析流式响应消息开始"""
        chunk = {
            "type": "message_start",
            "message": {
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": "claude-3-sonnet-20240229",
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 0
                }
            }
        }

        response = anthropic_provider._parse_stream_chunk(chunk)

        assert response.request_id == "msg_test"
        assert response.is_stream is True
        assert response.is_complete is False

    def test_parse_stream_chunk_content_delta(self, anthropic_provider):
        """测试解析流式响应内容增量"""
        chunk = {
            "type": "content_block_delta",
            "index": 0,
            "delta": {
                "type": "text_delta",
                "text": "Hello"
            }
        }

        response = anthropic_provider._parse_stream_chunk(chunk, "msg_test")

        assert response.request_id == "msg_test"
        assert response.content == "Hello"
        assert response.delta == "Hello"
        assert response.is_stream is True
        assert response.is_complete is False

    def test_parse_stream_chunk_message_stop(self, anthropic_provider):
        """测试解析流式响应消息结束"""
        chunk = {
            "type": "message_stop"
        }

        response = anthropic_provider._parse_stream_chunk(chunk, "msg_test")

        assert response.request_id == "msg_test"
        assert response.is_stream is True
        assert response.is_complete is True

    def test_get_supported_models(self, anthropic_provider):
        """测试获取支持的模型列表"""
        models = anthropic_provider.get_supported_models()
        assert isinstance(models, list)
        assert len(models) > 0
        assert "claude-3-opus-20240229" in models
        assert "claude-3-sonnet-20240229" in models
        assert "claude-3-haiku-20240307" in models

    def test_check_model_availability(self, anthropic_provider):
        """测试检查模型可用性"""
        assert anthropic_provider.check_model_availability("claude-3-sonnet-20240229") is True
        assert anthropic_provider.check_model_availability("claude-3-haiku-20240307") is True
        assert anthropic_provider.check_model_availability("unknown-model") is False

    def test_estimate_cost(self, anthropic_provider, sample_request):
        """测试成本估算"""
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_response.model = "claude-3-sonnet-20240229"
        mock_response.usage = {
            "prompt_tokens": 1000,
            "completion_tokens": 500
        }

        cost = anthropic_provider.estimate_cost(sample_request, mock_response)
        assert isinstance(cost, float)
        assert cost > 0

    @pytest.mark.asyncio
    async def test_complete_success(self, anthropic_provider, sample_request):
        """测试成功完成请求"""
        mock_response_data = {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Test response"}],
            "model": "claude-3-sonnet-20240229",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 5}
        }

        with patch.object(anthropic_provider.http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response_data

            response = await anthropic_provider.complete(sample_request)

            assert response.content == [{"type": "text", "text": "Test response"}]
            assert response.provider == "anthropic"
            assert response.finish_reason == "end_turn"

    @pytest.mark.asyncio
    async def test_stream_complete_success(self, anthropic_provider, sample_request):
        """测试成功流式完成请求"""
        chunks = [
            {"type": "message_start", "message": {"id": "msg_test"}},
            {"type": "content_block_delta", "delta": {"text": "Hello"}},
            {"type": "content_block_delta", "delta": {"text": " world!"}},
            {"type": "message_stop"}
        ]

        async def mock_stream_request(*args, **kwargs):
            for chunk in chunks:
                yield chunk

        with patch.object(anthropic_provider.http_client, 'stream_request') as mock_stream:
            mock_stream.return_value = mock_stream_request()

            responses = []
            async for response in anthropic_provider.stream_complete(sample_request):
                responses.append(response)

            assert len(responses) == 4
            assert responses[0].request_id == "msg_test"  # message_start
            assert responses[1].content == "Hello"
            assert responses[2].content == " world!"
            assert responses[3].is_complete is True  # message_stop