"""
测试LLM基础抽象类和数据模型
"""

import pytest
import time
from unittest.mock import Mock, patch
from src.llm.base import (
    MessageRole, Message, LLMConfig, LLMRequest, LLMResponse, LLMProvider
)


class TestMessageRole:
    """测试消息角色枚举"""

    def test_message_role_values(self):
        """测试消息角色枚举值"""
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.FUNCTION.value == "function"


class TestMessage:
    """测试消息数据类"""

    def test_message_creation(self):
        """测试消息创建"""
        message = Message(
            role=MessageRole.USER,
            content="Hello, world!"
        )
        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"
        assert message.name is None
        assert message.function_call is None
        assert message.metadata == {}

    def test_message_with_optional_fields(self):
        """测试包含可选字段的消息创建"""
        message = Message(
            role=MessageRole.ASSISTANT,
            content="I can help you",
            name="assistant",
            function_call={"name": "test", "arguments": "{}"},
            metadata={"source": "test"}
        )
        assert message.name == "assistant"
        assert message.function_call == {"name": "test", "arguments": "{}"}
        assert message.metadata == {"source": "test"}


class TestLLMConfig:
    """测试LLM配置数据类"""

    def test_config_creation(self):
        """测试配置创建"""
        config = LLMConfig(
            provider="openai",
            model="gpt-3.5-turbo",
            api_key="test-key"
        )
        assert config.provider == "openai"
        assert config.model == "gpt-3.5-turbo"
        assert config.api_key == "test-key"
        assert config.temperature == 0.7  # 默认值

    def test_config_validation_success(self):
        """测试配置验证成功"""
        config = LLMConfig(
            provider="openai",
            model="gpt-3.5-turbo",
            api_key="test-key",
            temperature=0.5,
            top_p=0.8
        )
        # 不应该抛出异常
        config.validate()

    def test_config_validation_missing_provider(self):
        """测试缺少提供者的配置验证"""
        config = LLMConfig(
            provider="",
            model="gpt-3.5-turbo",
            api_key="test-key"
        )
        with pytest.raises(ValueError, match="Provider is required"):
            config.validate()

    def test_config_validation_missing_model(self):
        """测试缺少模型的配置验证"""
        config = LLMConfig(
            provider="openai",
            model="",
            api_key="test-key"
        )
        with pytest.raises(ValueError, match="Model is required"):
            config.validate()

    def test_config_validation_invalid_temperature(self):
        """测试无效温度值的配置验证"""
        config = LLMConfig(
            provider="openai",
            model="gpt-3.5-turbo",
            api_key="test-key",
            temperature=3.0  # 超出范围
        )
        with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
            config.validate()

    def test_config_validation_invalid_top_p(self):
        """测试无效top_p值的配置验证"""
        config = LLMConfig(
            provider="openai",
            model="gpt-3.5-turbo",
            api_key="test-key",
            top_p=1.5  # 超出范围
        )
        with pytest.raises(ValueError, match="Top_p must be between 0 and 1"):
            config.validate()

    def test_config_validation_invalid_timeout(self):
        """测试无效超时时间的配置验证"""
        config = LLMConfig(
            provider="openai",
            model="gpt-3.5-turbo",
            api_key="test-key",
            timeout=0  # 非正数
        )
        with pytest.raises(ValueError, match="Timeout must be positive"):
            config.validate()

    def test_config_to_dict(self):
        """测试配置转换为字典"""
        config = LLMConfig(
            provider="openai",
            model="gpt-3.5-turbo",
            api_key="test-key",
            temperature=0.5,
            custom_params={"param1": "value1"}
        )
        config_dict = config.to_dict()
        assert config_dict["provider"] == "openai"
        assert config_dict["model"] == "gpt-3.5-turbo"
        assert config_dict["api_key"] == "test-key"
        assert config_dict["temperature"] == 0.5
        assert config_dict["custom_params"] == {"param1": "value1"}

    def test_config_from_dict(self):
        """测试从字典创建配置"""
        data = {
            "provider": "anthropic",
            "model": "claude-3-sonnet",
            "api_key": "test-key",
            "temperature": 0.8,
            "max_tokens": 2000
        }
        config = LLMConfig.from_dict(data)
        assert config.provider == "anthropic"
        assert config.model == "claude-3-sonnet"
        assert config.api_key == "test-key"
        assert config.temperature == 0.8
        assert config.max_tokens == 2000


class TestLLMRequest:
    """测试LLM请求数据类"""

    def test_request_creation(self):
        """测试请求创建"""
        config = LLMConfig(provider="openai", model="gpt-3.5-turbo")
        messages = [
            Message(role=MessageRole.USER, content="Hello")
        ]
        request = LLMRequest(messages=messages, config=config)
        assert len(request.messages) == 1
        assert request.config == config
        assert request.tools is None
        assert request.tool_choice is None
        assert len(request.request_id) > 0

    def test_add_message(self):
        """测试添加消息"""
        config = LLMConfig(provider="openai", model="gpt-3.5-turbo")
        request = LLMRequest(messages=[], config=config)

        request.add_message(MessageRole.USER, "Hello")
        assert len(request.messages) == 1
        assert request.messages[0].role == MessageRole.USER
        assert request.messages[0].content == "Hello"

    def test_get_last_message(self):
        """测试获取最后一条消息"""
        config = LLMConfig(provider="openai", model="gpt-3.5-turbo")
        request = LLMRequest(messages=[], config=config)

        assert request.get_last_message() is None

        request.add_message(MessageRole.USER, "First")
        request.add_message(MessageRole.ASSISTANT, "Second")

        last_message = request.get_last_message()
        assert last_message.content == "Second"
        assert last_message.role == MessageRole.ASSISTANT

    def test_request_to_dict(self):
        """测试请求转换为字典"""
        config = LLMConfig(provider="openai", model="gpt-3.5-turbo")
        messages = [Message(role=MessageRole.USER, content="Hello")]
        request = LLMRequest(
            messages=messages,
            config=config,
            tools=[{"type": "function", "function": {"name": "test"}}],
            metadata={"source": "test"}
        )

        request_dict = request.to_dict()
        assert "messages" in request_dict
        assert "config" in request_dict
        assert "tools" in request_dict
        assert "metadata" in request_dict
        assert len(request_dict["messages"]) == 1


class TestLLMResponse:
    """测试LLM响应数据类"""

    def test_response_creation(self):
        """测试响应创建"""
        response = LLMResponse(
            request_id="test-id",
            provider="openai",
            model="gpt-3.5-turbo",
            content="Hello back!",
            finish_reason="stop"
        )
        assert response.request_id == "test-id"
        assert response.provider == "openai"
        assert response.model == "gpt-3.5-turbo"
        assert response.content == "Hello back!"
        assert response.finish_reason == "stop"
        assert response.usage is None
        assert response.is_stream is False
        assert response.is_complete is True

    def test_response_with_usage(self):
        """测试包含使用信息的响应创建"""
        usage = {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15
        }
        response = LLMResponse(
            request_id="test-id",
            provider="openai",
            model="gpt-3.5-turbo",
            content="Hello back!",
            usage=usage
        )
        assert response.usage == usage

    def test_stream_response_creation(self):
        """测试流式响应创建"""
        response = LLMResponse(
            request_id="test-id",
            provider="openai",
            model="gpt-3.5-turbo",
            content="Hello",
            delta="Hello",
            is_stream=True,
            is_complete=False
        )
        assert response.is_stream is True
        assert response.is_complete is False
        assert response.delta == "Hello"

    def test_response_to_dict(self):
        """测试响应转换为字典"""
        usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        response = LLMResponse(
            request_id="test-id",
            provider="openai",
            model="gpt-3.5-turbo",
            content="Hello back!",
            usage=usage,
            metadata={"source": "test"}
        )

        response_dict = response.to_dict()
        assert response_dict["request_id"] == "test-id"
        assert response_dict["provider"] == "openai"
        assert response_dict["content"] == "Hello back!"
        assert response_dict["usage"] == usage
        assert response_dict["metadata"] == {"source": "test"}

    def test_response_from_dict(self):
        """测试从字典创建响应"""
        data = {
            "request_id": "test-id",
            "provider": "anthropic",
            "model": "claude-3-sonnet",
            "content": "Hello back!",
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}
        }
        response = LLMResponse.from_dict(data)
        assert response.request_id == "test-id"
        assert response.provider == "anthropic"
        assert response.content == "Hello back!"


class TestLLMProvider:
    """测试LLM提供者抽象基类"""

    def test_provider_is_abstract(self):
        """测试提供者是抽象类，不能直接实例化"""
        config = LLMConfig(provider="test", model="test-model")
        with pytest.raises(TypeError):
            LLMProvider(config)

    def test_concrete_provider_implementation(self):
        """测试具体提供者实现"""
        class TestProvider(LLMProvider):
            @property
            def provider_name(self) -> str:
                return "test"

            async def complete(self, request: LLMRequest) -> LLMResponse:
                return LLMResponse(
                    request_id=request.request_id,
                    provider=self.provider_name,
                    model=self.config.model,
                    content="Test response"
                )

            async def stream_complete(self, request: LLMRequest):
                yield LLMResponse(
                    request_id=request.request_id,
                    provider=self.provider_name,
                    model=self.config.model,
                    content="Stream response",
                    is_stream=True,
                    is_complete=True
                )

            def validate_request(self, request: LLMRequest) -> None:
                if not request.messages:
                    raise ValueError("Messages cannot be empty")

        config = LLMConfig(provider="test", model="test-model")
        provider = TestProvider(config)

        assert provider.provider_name == "test"
        assert provider.config == config

        # 测试默认配置
        default_config = provider.get_default_config()
        assert "temperature" in default_config
        assert "max_tokens" in default_config

        # 测试token估算
        token_count = provider.estimate_tokens("Hello, world!")
        assert token_count > 0

        # 测试成本估算
        request = LLMRequest(
            messages=[Message(role=MessageRole.USER, content="Hello")],
            config=config
        )
        response = LLMResponse(
            request_id="test",
            provider="test",
            model="test-model",
            content="Hi there!"
        )
        cost = provider.estimate_cost(request, response)
        assert isinstance(cost, float)
        assert cost >= 0

        # 测试请求头准备
        headers = provider.prepare_headers()
        assert "Content-Type" in headers
        assert "User-Agent" in headers

        # 测试请求数据准备
        data = provider.prepare_request_data(request)
        assert "model" in data
        assert "messages" in data

        # 测试请求验证
        # 有效请求不应该抛出异常
        provider.validate_request(request)

        # 空消息列表应该抛出异常
        empty_request = LLMRequest(messages=[], config=config)
        with pytest.raises(ValueError, match="Messages cannot be empty"):
            provider.validate_request(empty_request)