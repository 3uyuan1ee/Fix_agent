"""
LLM模块集成测试
"""

import pytest
import asyncio
import tempfile
import os
import yaml
from unittest.mock import Mock, AsyncMock, patch

from src.llm.config import LLMConfigManager
from src.llm.openai_provider import OpenAIProvider
from src.llm.anthropic_provider import AnthropicProvider
from src.llm.base import LLMConfig, LLMRequest, Message, MessageRole


class TestLLMIntegration:
    """LLM模块集成测试"""

    @pytest.fixture
    def integrated_config_file(self):
        """集成测试配置文件"""
        config_data = {
            "providers": {
                "openai": {
                    "provider": "openai",
                    "model": "gpt-3.5-turbo",
                    "api_key": "test-openai-key",
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "timeout": 30,
                    "max_retries": 3
                },
                "anthropic": {
                    "provider": "anthropic",
                    "model": "claude-3-sonnet-20240229",
                    "api_key": "test-anthropic-key",
                    "temperature": 0.5,
                    "max_tokens": 2000,
                    "timeout": 45,
                    "max_retries": 2
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        yield temp_file
        os.unlink(temp_file)

    @pytest.fixture
    def config_manager(self, integrated_config_file):
        """配置管理器fixture"""
        return LLMConfigManager(config_file=integrated_config_file)

    def test_config_manager_loads_multiple_providers(self, config_manager):
        """测试配置管理器加载多个提供者"""
        providers = config_manager.list_providers()
        assert len(providers) == 2
        assert "openai" in providers
        assert "anthropic" in providers

    def test_provider_creation_from_config(self, config_manager):
        """测试从配置创建提供者"""
        openai_config = config_manager.get_config("openai")
        openai_provider = OpenAIProvider(openai_config)

        assert openai_provider.provider_name == "openai"
        assert openai_provider.config.model == "gpt-3.5-turbo"
        assert openai_provider.config.api_key == "test-openai-key"

        anthropic_config = config_manager.get_config("anthropic")
        anthropic_provider = AnthropicProvider(anthropic_config)

        assert anthropic_provider.provider_name == "anthropic"
        assert anthropic_provider.config.model == "claude-3-sonnet-20240229"
        assert anthropic_provider.config.api_key == "test-anthropic-key"

    @pytest.mark.asyncio
    async def test_multiple_providers_concurrent_requests(self, config_manager):
        """测试多个提供者并发请求"""
        openai_config = config_manager.get_config("openai")
        anthropic_config = config_manager.get_config("anthropic")

        openai_provider = OpenAIProvider(openai_config)
        anthropic_provider = AnthropicProvider(anthropic_config)

        # 创建测试请求
        openai_request = LLMRequest(
            messages=[Message(role=MessageRole.USER, content="Hello OpenAI")],
            config=openai_config
        )

        anthropic_request = LLMRequest(
            messages=[
                Message(role=MessageRole.SYSTEM, content="You are helpful"),
                Message(role=MessageRole.USER, content="Hello Anthropic")
            ],
            config=anthropic_config
        )

        # 模拟API响应
        openai_response_data = {
            "id": "openai-test",
            "model": "gpt-3.5-turbo",
            "choices": [{
                "message": {"content": "OpenAI response"},
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8}
        }

        anthropic_response_data = {
            "id": "anthropic-test",
            "type": "message",
            "content": [{"type": "text", "text": "Anthropic response"}],
            "model": "claude-3-sonnet-20240229",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 5}
        }

        with patch.object(openai_provider.http_client, 'request', new_callable=AsyncMock) as mock_openai, \
             patch.object(anthropic_provider.http_client, 'request', new_callable=AsyncMock) as mock_anthropic:

            mock_openai.return_value = openai_response_data
            mock_anthropic.return_value = anthropic_response_data

            # 并发执行请求
            tasks = [
                openai_provider.complete(openai_request),
                anthropic_provider.complete(anthropic_request)
            ]

            results = await asyncio.gather(*tasks)

            openai_result, anthropic_result = results

            assert openai_result.content == "OpenAI response"
            assert openai_result.provider == "openai"
            assert anthropic_result.content == [{"type": "text", "text": "Anthropic response"}]
            assert anthropic_result.provider == "anthropic"

    @pytest.mark.asyncio
    async def test_provider_fallback_mechanism(self, config_manager):
        """测试提供者回退机制"""
        openai_config = config_manager.get_config("openai")
        anthropic_config = config_manager.get_config("anthropic")

        openai_provider = OpenAIProvider(openai_config)
        anthropic_provider = AnthropicProvider(anthropic_config)

        request = LLMRequest(
            messages=[Message(role=MessageRole.USER, content="Test message")],
            config=openai_config
        )

        # 模拟OpenAI失败，Anthropic成功
        anthropic_response_data = {
            "id": "anthropic-fallback",
            "type": "message",
            "content": [{"type": "text", "text": "Fallback response"}],
            "model": "claude-3-sonnet-20240229",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 5, "output_tokens": 3}
        }

        with patch.object(openai_provider.http_client, 'request', new_callable=AsyncMock) as mock_openai, \
             patch.object(anthropic_provider.http_client, 'request', new_callable=AsyncMock) as mock_anthropic:

            mock_openai.side_effect = Exception("OpenAI unavailable")
            mock_anthropic.return_value = anthropic_response_data

            # 尝试OpenAI，失败后使用Anthropic
            try:
                response = await openai_provider.complete(request)
                pytest.fail("Should have failed with OpenAI")
            except Exception:
                # 回退到Anthropic
                anthropic_request = LLMRequest(
                    messages=[
                        Message(role=MessageRole.SYSTEM, content="You are helpful"),
                        Message(role=MessageRole.USER, content="Test message")
                    ],
                    config=anthropic_config
                )
                response = await anthropic_provider.complete(anthropic_request)
                assert response.content == [{"type": "text", "text": "Fallback response"}]

    @pytest.mark.asyncio
    async def test_streaming_with_different_providers(self, config_manager):
        """测试不同提供者的流式响应机制"""
        openai_config = config_manager.get_config("openai")
        anthropic_config = config_manager.get_config("anthropic")

        openai_provider = OpenAIProvider(openai_config)
        anthropic_provider = AnthropicProvider(anthropic_config)

        # 测试流式响应接口调用
        async def mock_stream_data(*args, **kwargs):
            # 模拟单个流式响应片段
            yield {"id": "test", "model": "test", "choices": [{"delta": {"content": "test"}, "finish_reason": "stop"}]}

        with patch.object(openai_provider.http_client, 'stream_request') as mock_openai_stream, \
             patch.object(anthropic_provider.http_client, 'stream_request') as mock_anthropic_stream:

            mock_openai_stream.return_value = mock_stream_data()
            mock_anthropic_stream.return_value = mock_stream_data()

            # 测试OpenAI流式响应接口
            openai_request = LLMRequest(
                messages=[Message(role=MessageRole.USER, content="Test")],
                config=openai_config
            )

            openai_responses = []
            async for response in openai_provider.stream_complete(openai_request):
                openai_responses.append(response)
                break  # 只测试第一个响应

            assert len(openai_responses) >= 1
            assert openai_responses[0].provider == "openai"
            assert openai_responses[0].is_stream is True

            # 测试Anthropic流式响应接口
            anthropic_request = LLMRequest(
                messages=[Message(role=MessageRole.USER, content="Test")],
                config=anthropic_config
            )

            anthropic_responses = []
            async for response in anthropic_provider.stream_complete(anthropic_request):
                anthropic_responses.append(response)
                break  # 只测试第一个响应

            assert len(anthropic_responses) >= 1
            assert anthropic_responses[0].provider == "anthropic"
            assert anthropic_responses[0].is_stream is True

    def test_configuration_validation_across_providers(self, config_manager):
        """测试跨提供者的配置验证"""
        # 测试有效配置
        assert config_manager.validate_config("openai") is True
        assert config_manager.validate_config("anthropic") is True

        # 测试无效配置
        invalid_updates = {"temperature": 3.0}  # 超出范围
        result = config_manager.update_config("openai", invalid_updates)
        assert result is False

        # 验证原配置仍然有效
        assert config_manager.validate_config("openai") is True

    def test_cost_estimation_comparison(self, config_manager):
        """测试不同提供者的成本估算比较"""
        openai_config = config_manager.get_config("openai")
        anthropic_config = config_manager.get_config("anthropic")

        openai_provider = OpenAIProvider(openai_config)
        anthropic_provider = AnthropicProvider(anthropic_config)

        # 创建相同的请求
        messages = [Message(role=MessageRole.USER, content="Test message for cost comparison")]
        openai_request = LLMRequest(messages=messages, config=openai_config)
        anthropic_request = LLMRequest(messages=messages, config=anthropic_config)

        # 模拟响应
        mock_response = Mock()
        mock_response.content = "This is a test response for cost comparison"
        mock_response.usage = {
            "prompt_tokens": 10,
            "completion_tokens": 15
        }

        mock_response.model = "gpt-3.5-turbo"
        openai_cost = openai_provider.estimate_cost(openai_request, mock_response)

        mock_response.model = "claude-3-sonnet-20240229"
        anthropic_cost = anthropic_provider.estimate_cost(anthropic_request, mock_response)

        # 验证成本计算
        assert isinstance(openai_cost, float)
        assert isinstance(anthropic_cost, float)
        assert openai_cost > 0
        assert anthropic_cost > 0

    def test_token_estimation_comparison(self, config_manager):
        """测试不同提供者的token估算比较"""
        openai_config = config_manager.get_config("openai")
        anthropic_config = config_manager.get_config("anthropic")

        openai_provider = OpenAIProvider(openai_config)
        anthropic_provider = AnthropicProvider(anthropic_config)

        test_texts = [
            "Hello, world!",
            "你好，世界！",
            "This is a longer text with multiple sentences. It contains various characters and punctuation marks.",
            "这是一个更长的中文文本，包含多个句子和各种标点符号。"
        ]

        for text in test_texts:
            openai_tokens = openai_provider.estimate_tokens(text)
            anthropic_tokens = anthropic_provider.estimate_tokens(text)

            # 两种估算应该大致相近（允许一定差异）
            assert isinstance(openai_tokens, int)
            assert isinstance(anthropic_tokens, int)
            assert openai_tokens > 0
            assert anthropic_tokens > 0

            # 估算差异不应该太大
            ratio = max(openai_tokens, anthropic_tokens) / min(openai_tokens, anthropic_tokens)
            assert ratio < 2.0  # 差异不超过2倍

    def test_error_handling_consistency(self, config_manager):
        """测试错误处理的一致性"""
        openai_config = config_manager.get_config("openai")
        anthropic_config = config_manager.get_config("anthropic")

        openai_provider = OpenAIProvider(openai_config)
        anthropic_provider = AnthropicProvider(anthropic_config)

        # 测试无效请求验证
        empty_request = LLMRequest(messages=[], config=openai_config)

        with pytest.raises(ValueError, match="Messages cannot be empty"):
            openai_provider.validate_request(empty_request)

        with pytest.raises(ValueError, match="Messages cannot be empty"):
            anthropic_provider.validate_request(empty_request)

        # 测试空内容消息验证
        empty_content_request = LLMRequest(
            messages=[Message(role=MessageRole.USER, content="   ")],
            config=openai_config
        )

        with pytest.raises(ValueError, match="Message content cannot be empty"):
            openai_provider.validate_request(empty_content_request)

        with pytest.raises(ValueError, match="Message content cannot be empty"):
            anthropic_provider.validate_request(empty_content_request)

    @pytest.mark.asyncio
    async def test_provider_isolation(self, config_manager):
        """测试提供者之间的隔离性"""
        openai_config = config_manager.get_config("openai")
        anthropic_config = config_manager.get_config("anthropic")

        openai_provider = OpenAIProvider(openai_config)
        anthropic_provider = AnthropicProvider(anthropic_config)

        # 验证提供者配置隔离
        assert openai_provider.config != anthropic_provider.config
        assert openai_provider.provider_name != anthropic_provider.provider_name

        # 验证HTTP客户端隔离
        assert openai_provider.http_client != anthropic_provider.http_client

        # 验证独立操作
        openai_request = LLMRequest(
            messages=[Message(role=MessageRole.USER, content="OpenAI test")],
            config=openai_config
        )

        anthropic_request = LLMRequest(
            messages=[Message(role=MessageRole.USER, content="Anthropic test")],
            config=anthropic_config
        )

        openai_response_data = {
            "id": "openai-isolated",
            "model": "gpt-3.5-turbo",
            "choices": [{"message": {"content": "OpenAI isolated response"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}
        }

        anthropic_response_data = {
            "id": "anthropic-isolated",
            "type": "message",
            "content": [{"type": "text", "text": "Anthropic isolated response"}],
            "model": "claude-3-sonnet-20240229",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 8, "output_tokens": 6}
        }

        with patch.object(openai_provider.http_client, 'request', new_callable=AsyncMock) as mock_openai, \
             patch.object(anthropic_provider.http_client, 'request', new_callable=AsyncMock) as mock_anthropic:

            mock_openai.return_value = openai_response_data
            mock_anthropic.return_value = anthropic_response_data

            # 并发独立请求
            openai_result = await openai_provider.complete(openai_request)
            anthropic_result = await anthropic_provider.complete(anthropic_request)

            assert openai_result.content == "OpenAI isolated response"
            assert anthropic_result.content == [{"type": "text", "text": "Anthropic isolated response"}]

            # 验证调用次数正确
            assert mock_openai.call_count == 1
            assert mock_anthropic.call_count == 1