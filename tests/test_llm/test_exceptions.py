"""
测试LLM异常类
"""

import pytest
from src.llm.exceptions import (
    LLMError, LLMConfigError, LLMTimeoutError, LLMRateLimitError,
    LLMNetworkError, LLMAuthenticationError, LLMQuotaExceededError,
    LLMModelNotFoundError, LLMTokenLimitError, LLMContentFilterError,
    LLMProviderUnavailableError
)


class TestLLMError:
    """测试基础LLM异常"""

    def test_llm_error_creation(self):
        """测试基础LLM异常创建"""
        error = LLMError("Test error")
        assert str(error) == "Test error"
        assert error.provider is None
        assert error.error_code is None
        assert error.details is None

    def test_llm_error_with_all_parameters(self):
        """测试包含所有参数的LLM异常创建"""
        details = {"retry_after": 5}
        error = LLMError(
            message="Detailed error",
            provider="openai",
            error_code="401",
            details=details
        )
        assert str(error) == "Detailed error (provider: openai, code: 401)"
        assert error.provider == "openai"
        assert error.error_code == "401"
        assert error.details == details

    def test_llm_error_str_with_provider(self):
        """测试包含提供者信息的异常字符串表示"""
        error = LLMError(
            message="Error occurred",
            provider="anthropic",
            error_code="429"
        )
        expected_str = "Error occurred (provider: anthropic, code: 429)"
        assert str(error) == expected_str

    def test_llm_error_repr(self):
        """测试异常的repr表示"""
        error = LLMError(
            message="Test error",
            provider="test",
            error_code="500"
        )
        expected = "LLMError('Test error', provider='test', code='500')"
        assert repr(error) == expected


class TestLLMConfigError:
    """测试LLM配置异常"""

    def test_config_error_creation(self):
        """测试配置异常创建"""
        error = LLMConfigError("Invalid configuration")
        assert str(error) == "Invalid configuration"
        assert isinstance(error, LLMError)


class TestLLMTimeoutError:
    """测试LLM超时异常"""

    def test_timeout_error_creation(self):
        """测试超时异常创建"""
        error = LLMTimeoutError("Request timed out")
        assert str(error) == "Request timed out"
        assert isinstance(error, LLMError)

    def test_timeout_error_with_details(self):
        """测试包含详细信息的超时异常"""
        details = {"timeout_seconds": 30, "attempt": 3}
        error = LLMTimeoutError(
            message="Request timed out after 30 seconds",
            provider="openai",
            error_code="timeout",
            details=details
        )
        assert error.provider == "openai"
        assert error.error_code == "timeout"
        assert error.details["timeout_seconds"] == 30


class TestLLMRateLimitError:
    """测试LLM速率限制异常"""

    def test_rate_limit_error_creation(self):
        """测试速率限制异常创建"""
        error = LLMRateLimitError("Rate limit exceeded")
        assert str(error) == "Rate limit exceeded"
        assert isinstance(error, LLMError)
        assert error.retry_after is None

    def test_rate_limit_error_with_retry_after(self):
        """测试包含重试时间的速率限制异常"""
        error = LLMRateLimitError(
            message="Rate limit exceeded",
            provider="anthropic",
            error_code="429",
            retry_after=60
        )
        assert error.retry_after == 60
        assert error.provider == "anthropic"


class TestLLMNetworkError:
    """测试LLM网络异常"""

    def test_network_error_creation(self):
        """测试网络异常创建"""
        error = LLMNetworkError("Network connection failed")
        assert str(error) == "Network connection failed"
        assert isinstance(error, LLMError)


class TestLLMAuthenticationError:
    """测试LLM认证异常"""

    def test_authentication_error_creation(self):
        """测试认证异常创建"""
        error = LLMAuthenticationError("Authentication failed")
        assert str(error) == "Authentication failed"
        assert isinstance(error, LLMError)


class TestLLMQuotaExceededError:
    """测试LLM配额超限异常"""

    def test_quota_exceeded_error_creation(self):
        """测试配额超限异常创建"""
        error = LLMQuotaExceededError("Quota exceeded")
        assert str(error) == "Quota exceeded"
        assert isinstance(error, LLMError)


class TestLLMModelNotFoundError:
    """测试LLM模型未找到异常"""

    def test_model_not_found_error_creation(self):
        """测试模型未找到异常创建"""
        error = LLMModelNotFoundError("Model not found")
        assert str(error) == "Model not found"
        assert isinstance(error, LLMError)


class TestLLMTokenLimitError:
    """测试LLM令牌限制异常"""

    def test_token_limit_error_creation(self):
        """测试令牌限制异常创建"""
        error = LLMTokenLimitError("Token limit exceeded")
        assert str(error) == "Token limit exceeded"
        assert isinstance(error, LLMError)


class TestLLMContentFilterError:
    """测试LLM内容过滤异常"""

    def test_content_filter_error_creation(self):
        """测试内容过滤异常创建"""
        error = LLMContentFilterError("Content filtered")
        assert str(error) == "Content filtered"
        assert isinstance(error, LLMError)


class TestLLMProviderUnavailableError:
    """测试LLM提供者不可用异常"""

    def test_provider_unavailable_error_creation(self):
        """测试提供者不可用异常创建"""
        error = LLMProviderUnavailableError("Provider unavailable")
        assert str(error) == "Provider unavailable"
        assert isinstance(error, LLMError)


class TestExceptionHierarchy:
    """测试异常层次结构"""

    def test_all_exceptions_inherit_from_llm_error(self):
        """测试所有异常都继承自LLMError"""
        exception_classes = [
            LLMConfigError,
            LLMTimeoutError,
            LLMRateLimitError,
            LLMNetworkError,
            LLMAuthenticationError,
            LLMQuotaExceededError,
            LLMModelNotFoundError,
            LLMTokenLimitError,
            LLMContentFilterError,
            LLMProviderUnavailableError
        ]

        for exc_class in exception_classes:
            # 创建异常实例
            error = exc_class("Test message")
            # 验证继承关系
            assert isinstance(error, LLMError)
            assert isinstance(error, Exception)

    def test_exception_catching(self):
        """测试异常捕获"""
        try:
            raise LLMTimeoutError("Timeout occurred")
        except LLMError as e:
            assert isinstance(e, LLMTimeoutError)
            assert str(e) == "Timeout occurred"
        except Exception:
            pytest.fail("Should have been caught by LLMError")

    def test_specific_exception_catching(self):
        """测试特定异常捕获"""
        try:
            raise LLMRateLimitError("Rate limit hit", retry_after=30)
        except LLMRateLimitError as e:
            assert e.retry_after == 30
        except LLMError:
            pytest.fail("Should have been caught by specific exception")

    def test_exception_with_none_provider(self):
        """测试没有提供者的异常"""
        error = LLMError("Generic error")
        assert error.provider is None

        # 字符串表示不应该包含提供者信息
        error_str = str(error)
        assert "provider:" not in error_str