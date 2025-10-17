#!/usr/bin/env python3
"""
ZhipuProvider单元测试
"""

import unittest
import asyncio
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.llm.zhipu_provider import ZhipuProvider, ZHIPU_AVAILABLE
from src.llm.base import LLMConfig, LLMRequest, LLMResponse, Message, MessageRole
from src.llm.exceptions import (
    LLMError, LLMTimeoutError, LLMRateLimitError,
    LLMNetworkError, LLMAuthenticationError, LLMProviderUnavailableError
)


class TestZhipuProvider(unittest.TestCase):
    """ZhipuProvider测试类"""

    def setUp(self):
        """测试前准备"""
        self.config = LLMConfig(
            provider="zhipu",
            model="glm-4.5",
            api_key="test-api-key",
            api_base="https://open.bigmodel.cn/api/paas/v4/",
            temperature=0.7,
            max_tokens=1000
        )

    @unittest.skipUnless(ZHIPU_AVAILABLE, "zai-sdk not available")
    def test_provider_initialization_success(self):
        """测试提供者初始化成功"""
        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', True):
            with patch('src.llm.zhipu_provider.ZhipuAiClient'):
                provider = ZhipuProvider(self.config)
                self.assertEqual(provider.provider_name, "zhipu")
                self.assertEqual(provider.config.model, "glm-4.5")

    def test_provider_initialization_without_sdk(self):
        """测试没有SDK时的初始化失败"""
        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', False):
            with self.assertRaises(LLMProviderUnavailableError):
                ZhipuProvider(self.config)

    @unittest.skipUnless(ZHIPU_AVAILABLE, "zai-sdk not available")
    def test_provider_initialization_invalid_config(self):
        """测试无效配置的初始化失败"""
        invalid_config = LLMConfig(
            provider="zhipu",
            model="",  # 空模型名
            api_key="test-api-key"
        )

        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', True):
            with self.assertRaises(ValueError):
                ZhipuProvider(invalid_config)

    @unittest.skipUnless(ZHIPU_AVAILABLE, "zai-sdk not available")
    def test_validate_request_valid(self):
        """测试有效请求验证"""
        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', True):
            with patch('src.llm.zhipu_provider.ZhipuAiClient'):
                provider = ZhipuProvider(self.config)

                request = LLMRequest(
                    messages=[
                        Message(MessageRole.USER, "Hello")
                    ],
                    config=self.config
                )

                # 应该不抛出异常
                provider.validate_request(request)

    @unittest.skipUnless(ZHIPU_AVAILABLE, "zai-sdk not available")
    def test_validate_request_empty_messages(self):
        """测试空消息验证失败"""
        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', True):
            with patch('src.llm.zhipu_provider.ZhipuAiClient'):
                provider = ZhipuProvider(self.config)

                request = LLMRequest(
                    messages=[],
                    config=self.config
                )

                with self.assertRaises(ValueError):
                    provider.validate_request(request)

    @unittest.skipUnless(ZHIPU_AVAILABLE, "zai-sdk not available")
    async def test_complete_success(self):
        """测试成功完成请求"""
        # 模拟响应
        mock_response = Mock()
        mock_response.model = "glm-4.5"
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Hello! How can I help you?"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.choices[0].message.tool_calls = None

        mock_usage = Mock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 5
        mock_usage.total_tokens = 15
        mock_response.usage = mock_usage

        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', True):
            with patch('src.llm.zhipu_provider.ZhipuAiClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.chat.completions.create.return_value = mock_response

                provider = ZhipuProvider(self.config)

                request = LLMRequest(
                    messages=[
                        Message(MessageRole.USER, "Hello")
                    ],
                    config=self.config
                )

                response = await provider.complete(request)

                self.assertIsInstance(response, LLMResponse)
                self.assertEqual(response.provider, "zhipu")
                self.assertEqual(response.model, "glm-4.5")
                self.assertEqual(response.content, "Hello! How can I help you?")
                self.assertEqual(response.finish_reason, "stop")
                self.assertEqual(response.usage["prompt_tokens"], 10)
                self.assertEqual(response.usage["completion_tokens"], 5)
                self.assertEqual(response.usage["total_tokens"], 15)

    @unittest.skipUnless(ZHIPU_AVAILABLE, "zai-sdk not available")
    async def test_complete_with_tools(self):
        """测试带工具调用的请求"""
        # 模拟响应
        mock_response = Mock()
        mock_response.model = "glm-4.5"
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = None
        mock_response.choices[0].finish_reason = "tool_calls"

        # 模拟工具调用
        mock_tool_call = Mock()
        mock_tool_call.id = "call_123"
        mock_tool_call.type = "function"
        mock_tool_call.function.name = "get_weather"
        mock_tool_call.function.arguments = '{"location": "北京"}'
        mock_response.choices[0].message.tool_calls = [mock_tool_call]

        mock_usage = Mock()
        mock_usage.prompt_tokens = 20
        mock_usage.completion_tokens = 10
        mock_usage.total_tokens = 30
        mock_response.usage = mock_usage

        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', True):
            with patch('src.llm.zhipu_provider.ZhipuAiClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.chat.completions.create.return_value = mock_response

                provider = ZhipuProvider(self.config)

                tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "description": "获取天气信息",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "location": {"type": "string"}
                                }
                            }
                        }
                    }
                ]

                request = LLMRequest(
                    messages=[
                        Message(MessageRole.USER, "北京今天天气怎么样？")
                    ],
                    config=self.config,
                    tools=tools
                )

                response = await provider.complete(request)

                self.assertIsInstance(response, LLMResponse)
                self.assertEqual(response.provider, "zhipu")
                self.assertEqual(response.model, "glm-4.5")
                self.assertEqual(response.finish_reason, "tool_calls")
                self.assertIsNotNone(response.tool_calls)
                self.assertEqual(len(response.tool_calls), 1)
                self.assertEqual(response.tool_calls[0]["function"]["name"], "get_weather")

    @unittest.skipUnless(ZHIPU_AVAILABLE, "zai-sdk not available")
    async def test_complete_api_error(self):
        """测试API错误处理"""
        import zai

        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', True):
            with patch('src.llm.zhipu_provider.ZhipuAiClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.chat.completions.create.side_effect = zai.core.APIError("API Error")

                provider = ZhipuProvider(self.config)

                request = LLMRequest(
                    messages=[
                        Message(MessageRole.USER, "Hello")
                    ],
                    config=self.config
                )

                with self.assertRaises(LLMError):
                    await provider.complete(request)

    @unittest.skipUnless(ZHIPU_AVAILABLE, "zai-sdk not available")
    async def test_complete_auth_error(self):
        """测试认证错误处理"""
        import zai

        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', True):
            with patch('src.llm.zhipu_provider.ZhipuAiClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.chat.completions.create.side_effect = zai.core.AuthenticationError("Invalid API key")

                provider = ZhipuProvider(self.config)

                request = LLMRequest(
                    messages=[
                        Message(MessageRole.USER, "Hello")
                    ],
                    config=self.config
                )

                with self.assertRaises(LLMAuthenticationError):
                    await provider.complete(request)

    @unittest.skipUnless(ZHIPU_AVAILABLE, "zai-sdk not available")
    async def test_complete_rate_limit_error(self):
        """测试速率限制错误处理"""
        import zai

        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', True):
            with patch('src.llm.zhipu_provider.ZhipuAiClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.chat.completions.create.side_effect = zai.core.RateLimitError("Rate limit exceeded")

                provider = ZhipuProvider(self.config)

                request = LLMRequest(
                    messages=[
                        Message(MessageRole.USER, "Hello")
                    ],
                    config=self.config
                )

                with self.assertRaises(LLMRateLimitError):
                    await provider.complete(request)

    @unittest.skipUnless(ZHIPU_AVAILABLE, "zai-sdk not available")
    async def test_stream_complete(self):
        """测试流式完成"""
        # 模拟流式响应
        mock_chunks = [
            Mock(choices=[Mock(delta=Mock(content="Hello"))]),
            Mock(choices=[Mock(delta=Mock(content=" world"))]),
            Mock(choices=[Mock(delta=Mock(content="!"))]),
            Mock(choices=[Mock(delta=Mock(content=None), finish_reason="stop")])
        ]

        mock_stream = Mock()
        mock_stream.__iter__ = Mock(return_value=iter(mock_chunks))

        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', True):
            with patch('src.llm.zhipu_provider.ZhipuAiClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.chat.completions.create.return_value = mock_stream

                provider = ZhipuProvider(self.config)

                request = LLMRequest(
                    messages=[
                        Message(MessageRole.USER, "Say hello")
                    ],
                    config=self.config
                )

                responses = []
                async for response in provider.stream_complete(request):
                    responses.append(response)

                self.assertEqual(len(responses), 4)
                self.assertEqual(responses[0].content, "Hello")
                self.assertEqual(responses[1].content, " world")
                self.assertEqual(responses[2].content, "!")
                self.assertEqual(responses[3].content, "")
                self.assertTrue(responses[3].is_complete)

    @unittest.skipUnless(ZHIPU_AVAILABLE, "zai-sdk not available")
    def test_convert_messages(self):
        """测试消息格式转换"""
        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', True):
            with patch('src.llm.zhipu_provider.ZhipuAiClient'):
                provider = ZhipuProvider(self.config)

                messages = [
                    Message(MessageRole.SYSTEM, "You are a helpful assistant"),
                    Message(MessageRole.USER, "Hello", name="user1"),
                    Message(MessageRole.ASSISTANT, "Hi there!")
                ]

                converted = provider._convert_messages(messages)

                self.assertEqual(len(converted), 3)
                self.assertEqual(converted[0]["role"], "system")
                self.assertEqual(converted[0]["content"], "You are a helpful assistant")
                self.assertEqual(converted[1]["role"], "user")
                self.assertEqual(converted[1]["content"], "Hello")
                self.assertEqual(converted[1]["name"], "user1")
                self.assertEqual(converted[2]["role"], "assistant")
                self.assertEqual(converted[2]["content"], "Hi there!")

    @unittest.skipUnless(ZHIPU_AVAILABLE, "zai-sdk not available")
    def test_get_default_config(self):
        """测试获取默认配置"""
        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', True):
            with patch('src.llm.zhipu_provider.ZhipuAiClient'):
                provider = ZhipuProvider(self.config)

                default_config = provider.get_default_config()

                self.assertEqual(default_config["model"], "glm-4.5")
                self.assertEqual(default_config["api_base"], "https://open.bigmodel.cn/api/paas/v4/")
                self.assertEqual(default_config["max_tokens"], 4000)
                self.assertEqual(default_config["temperature"], 0.7)

    @unittest.skipUnless(ZHIPU_AVAILABLE, "zai-sdk not available")
    def test_estimate_tokens(self):
        """测试token估算"""
        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', True):
            with patch('src.llm.zhipu_provider.ZhipuAiClient'):
                provider = ZhipuProvider(self.config)

                # 测试英文文本
                english_tokens = provider.estimate_tokens("Hello world")
                self.assertGreater(english_tokens, 0)

                # 测试中文文本
                chinese_tokens = provider.estimate_tokens("你好世界")
                self.assertGreater(chinese_tokens, 0)

                # 中文和英文的token数量都应该大于0
                self.assertGreater(chinese_tokens, 0)
                self.assertGreater(english_tokens, 0)

    @unittest.skipUnless(ZHIPU_AVAILABLE, "zai-sdk not available")
    def test_estimate_cost(self):
        """测试成本估算"""
        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', True):
            with patch('src.llm.zhipu_provider.ZhipuAiClient'):
                provider = ZhipuProvider(self.config)

                request = LLMRequest(
                    messages=[
                        Message(MessageRole.USER, "Hello")
                    ],
                    config=self.config
                )

                response = LLMResponse(
                    request_id="test",
                    provider="zhipu",
                    model="glm-4.5",
                    content="Hi there!",
                    usage={
                        "prompt_tokens": 10,
                        "completion_tokens": 5,
                        "total_tokens": 15
                    }
                )

                cost = provider.estimate_cost(request, response)
                self.assertGreater(cost, 0)

    @unittest.skipUnless(ZHIPU_AVAILABLE, "zai-sdk not available")
    def test_supports_function_calling(self):
        """测试函数调用支持"""
        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', True):
            with patch('src.llm.zhipu_provider.ZhipuAiClient'):
                provider = ZhipuProvider(self.config)
                self.assertTrue(provider.supports_function_calling())

    @unittest.skipUnless(ZHIPU_AVAILABLE, "zai-sdk not available")
    def test_supports_streaming(self):
        """测试流式响应支持"""
        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', True):
            with patch('src.llm.zhipu_provider.ZhipuAiClient'):
                provider = ZhipuProvider(self.config)
                self.assertTrue(provider.supports_streaming())

    @unittest.skipUnless(ZHIPU_AVAILABLE, "zai-sdk not available")
    def test_supports_vision(self):
        """测试视觉理解支持"""
        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', True):
            with patch('src.llm.zhipu_provider.ZhipuAiClient'):
                # GLM-4V模型支持视觉
                vision_config = LLMConfig(
                    provider="zhipu",
                    model="glm-4v",
                    api_key="test-api-key"
                )
                vision_provider = ZhipuProvider(vision_config)
                self.assertTrue(vision_provider.supports_vision())

                # GLM-4.5模型不支持视觉
                text_config = LLMConfig(
                    provider="zhipu",
                    model="glm-4.5",
                    api_key="test-api-key"
                )
                text_provider = ZhipuProvider(text_config)
                self.assertFalse(text_provider.supports_vision())

    @unittest.skipUnless(ZHIPU_AVAILABLE, "zai-sdk not available")
    def test_supports_embeddings(self):
        """测试文本嵌入支持"""
        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', True):
            with patch('src.llm.zhipu_provider.ZhipuAiClient'):
                # 嵌入模型支持嵌入
                embedding_config = LLMConfig(
                    provider="zhipu",
                    model="embedding-3",
                    api_key="test-api-key"
                )
                embedding_provider = ZhipuProvider(embedding_config)
                self.assertTrue(embedding_provider.supports_embeddings())

                # 聊天模型不支持嵌入
                chat_config = LLMConfig(
                    provider="zhipu",
                    model="glm-4.5",
                    api_key="test-api-key"
                )
                chat_provider = ZhipuProvider(chat_config)
                self.assertFalse(chat_provider.supports_embeddings())

    @unittest.skipUnless(ZHIPU_AVAILABLE, "zai-sdk not available")
    def test_get_provider_models(self):
        """测试获取支持的模型列表"""
        with patch('src.llm.zhipu_provider.ZHIPU_AVAILABLE', True):
            with patch('src.llm.zhipu_provider.ZhipuAiClient'):
                provider = ZhipuProvider(self.config)

                models = provider.get_provider_models()

                self.assertIsInstance(models, list)
                self.assertIn("glm-4.5", models)
                self.assertIn("glm-4v", models)
                self.assertIn("embedding-3", models)


if __name__ == '__main__':
    unittest.main()