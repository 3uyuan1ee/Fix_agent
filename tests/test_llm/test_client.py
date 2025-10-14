"""
测试LLM客户端
"""

import pytest
import asyncio
import tempfile
import os
import yaml
from unittest.mock import Mock, AsyncMock, patch

from src.llm.client import LLMClient, LLMClientConfig
from src.llm.config import LLMConfigManager
from src.llm.base import LLMRequest, Message, MessageRole
from src.llm.exceptions import LLMError


class TestLLMClientConfig:
    """测试LLM客户端配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = LLMClientConfig()
        assert config.default_provider == "openai"
        assert config.fallback_providers == ["anthropic"]
        assert config.enable_fallback is True
        assert config.max_retry_attempts == 3
        assert config.timeout == 30

    def test_custom_config(self):
        """测试自定义配置"""
        config = LLMClientConfig(
            default_provider="anthropic",
            fallback_providers=["openai"],
            enable_fallback=False,
            max_retry_attempts=5,
            timeout=60
        )
        assert config.default_provider == "anthropic"
        assert config.fallback_providers == ["openai"]
        assert config.enable_fallback is False
        assert config.max_retry_attempts == 5
        assert config.timeout == 60

    def test_config_from_dict(self):
        """测试从字典创建配置"""
        config_dict = {
            "default_provider": "anthropic",
            "enable_fallback": True
        }
        config = LLMClientConfig(**config_dict)
        assert config.default_provider == "anthropic"
        assert config.enable_fallback is True
        assert config.fallback_providers == ["anthropic"]  # 默认值


class TestLLMClient:
    """测试LLM客户端"""

    @pytest.fixture
    def config_file(self):
        """测试配置文件"""
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
    def config_manager(self, config_file):
        """配置管理器fixture"""
        return LLMConfigManager(config_file=config_file)

    @pytest.fixture
    def client(self, config_manager):
        """LLM客户端fixture"""
        return LLMClient(config_manager=config_manager)

    def test_client_initialization(self, client):
        """测试客户端初始化"""
        assert client is not None
        assert "openai" in client.get_provider_names()
        assert "anthropic" in client.get_provider_names()
        assert client.config.default_provider == "openai"

    def test_client_initialization_with_config(self, config_manager):
        """测试使用自定义配置初始化客户端"""
        config = LLMClientConfig(
            default_provider="anthropic",
            enable_fallback=False
        )
        client = LLMClient(config=config, config_manager=config_manager)
        assert client.config.default_provider == "anthropic"
        assert client.config.enable_fallback is False

    def test_create_request_from_strings(self, client):
        """测试从字符串创建请求"""
        request = client.create_request(["Hello", "How are you?"])
        assert len(request.messages) == 2
        assert request.messages[0].role == MessageRole.USER
        assert request.messages[0].content == "Hello"
        assert request.messages[1].role == MessageRole.USER
        assert request.messages[1].content == "How are you?"

    def test_create_request_from_messages(self, client):
        """测试从Message对象创建请求"""
        messages = [
            Message(role=MessageRole.SYSTEM, content="You are helpful"),
            Message(role=MessageRole.USER, content="Hello")
        ]
        request = client.create_request(messages)
        assert len(request.messages) == 2
        assert request.messages[0].role == MessageRole.SYSTEM
        assert request.messages[1].role == MessageRole.USER

    def test_get_provider_names(self, client):
        """测试获取提供者名称"""
        providers = client.get_provider_names()
        assert isinstance(providers, list)
        assert "openai" in providers
        assert "anthropic" in providers

    def test_get_stats(self, client):
        """测试获取统计信息"""
        stats = client.get_stats()
        assert "total_requests" in stats
        assert "successful_requests" in stats
        assert "failed_requests" in stats
        assert "success_rate" in stats
        assert "fallback_rate" in stats
        assert "provider_usage" in stats

    def test_reset_stats(self, client):
        """测试重置统计信息"""
        # 先添加一些统计
        client.stats["total_requests"] = 10
        client.stats["successful_requests"] = 8

        # 重置
        client.reset_stats()

        # 验证重置
        stats = client.get_stats()
        assert stats["total_requests"] == 0
        assert stats["successful_requests"] == 0

    @pytest.mark.asyncio
    async def test_successful_completion(self, client):
        """测试成功的完成请求"""
        # 模拟响应
        mock_response_data = {
            "id": "test-id",
            "model": "gpt-3.5-turbo",
            "choices": [{
                "message": {"content": "Hello! How can I help you?"},
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25}
        }

        request = client.create_request(["Hello"])

        with patch.object(client.providers["openai"], 'complete', new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = Mock(
                content="Hello! How can I help you?",
                model="gpt-3.5-turbo",
                provider="openai",
                usage={"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25}
            )

            response = await client.complete(request)

            assert response.content == "Hello! How can I help you?"
            assert response.provider == "openai"
            assert response.model == "gpt-3.5-turbo"

            # 验证统计更新
            stats = client.get_stats()
            assert stats["total_requests"] == 1
            assert stats["successful_requests"] == 1
            assert stats["provider_usage"]["openai"] == 1

    @pytest.mark.asyncio
    async def test_fallback_mechanism(self, client):
        """测试回退机制"""
        request = client.create_request(["Hello"])

        with patch.object(client.providers["openai"], 'complete', new_callable=AsyncMock) as mock_openai, \
             patch.object(client.providers["anthropic"], 'complete', new_callable=AsyncMock) as mock_anthropic:

            # OpenAI失败，Anthropic成功
            mock_openai.side_effect = Exception("OpenAI unavailable")
            mock_anthropic.return_value = Mock(
                content="Hello from Anthropic!",
                model="claude-3-sonnet-20240229",
                provider="anthropic"
            )

            response = await client.complete(request)

            assert response.content == "Hello from Anthropic!"
            assert response.provider == "anthropic"

            # 验证回退统计
            stats = client.get_stats()
            assert stats["successful_requests"] == 1
            assert stats["fallback_used"] == 1
            assert stats["provider_usage"]["anthropic"] == 1

    @pytest.mark.asyncio
    async def test_stream_completion(self, client):
        """测试流式完成"""
        request = client.create_request(["Hello"])

        async def mock_stream_generator(*args, **kwargs):
            yield Mock(content="Hello ", delta="Hello ")
            yield Mock(content="world!", delta="world!")

        with patch.object(client.providers["openai"], 'stream_complete') as mock_stream:
            mock_stream.return_value = mock_stream_generator()

            chunks = []
            async for chunk in client.stream_complete(request):
                chunks.append(chunk)

            assert len(chunks) == 2
            assert chunks[0].content == "Hello "
            assert chunks[1].content == "world!"

    @pytest.mark.asyncio
    async def test_test_connection_success(self, client):
        """测试连接测试成功"""
        with patch.object(client, 'complete', new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = Mock(
                content="Connection successful",
                model="gpt-3.5-turbo",
                provider="openai"
            )

            results = await client.test_connection("openai")

            assert "openai" in results
            assert results["openai"]["status"] == "success"
            assert "response_time" in results["openai"]
            assert results["openai"]["model"] == "gpt-3.5-turbo"

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, client):
        """测试连接测试失败"""
        with patch.object(client, 'complete', new_callable=AsyncMock) as mock_complete:
            mock_complete.side_effect = Exception("Connection failed")

            results = await client.test_connection("openai")

            assert "openai" in results
            assert results["openai"]["status"] == "failed"
            assert "error" in results["openai"]

    @pytest.mark.asyncio
    async def test_test_connection_all_providers(self, client):
        """测试所有提供者的连接"""
        with patch.object(client, 'complete', new_callable=AsyncMock) as mock_complete:
            # 第一个提供者成功，第二个失败
            def side_effect_func(*args, **kwargs):
                if "provider" in kwargs and kwargs["provider"] == "anthropic":
                    raise Exception("Anthropic failed")
                return Mock(
                    content="Success",
                    model="gpt-3.5-turbo",
                    provider="openai"
                )

            mock_complete.side_effect = side_effect_func

            results = await client.test_connection()

            assert len(results) == 2
            assert results["openai"]["status"] == "success"
            assert results["anthropic"]["status"] == "failed"

    def test_no_available_providers(self):
        """测试没有可用提供者的情况"""
        # 创建没有提供者的配置管理器
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({"providers": {}}, f)
            temp_file = f.name

        try:
            config_manager = LLMConfigManager(config_file=temp_file)
            with pytest.raises(LLMError, match="No LLM providers available"):
                LLMClient(config_manager=config_manager)
        finally:
            os.unlink(temp_file)