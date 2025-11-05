"""
LLM接口异常类定义
"""


class LLMError(Exception):
    """LLM基础异常类"""

    def __init__(
        self,
        message: str,
        provider: str = None,
        error_code: str = None,
        details: dict = None,
    ):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.error_code = error_code
        self.details = details

    def __str__(self):
        """返回异常字符串表示"""
        if self.provider and self.error_code:
            return (
                f"{self.message} (provider: {self.provider}, code: {self.error_code})"
            )
        return self.message

    def __repr__(self):
        """返回异常的repr表示"""
        if self.provider and self.error_code:
            return f"{self.__class__.__name__}('{self.message}', provider='{self.provider}', code='{self.error_code}')"
        return f"{self.__class__.__name__}('{self.message}')"


class LLMConfigError(LLMError):
    """LLM配置异常"""

    pass


class LLMTimeoutError(LLMError):
    """LLM请求超时异常"""

    pass


class LLMRateLimitError(LLMError):
    """LLM速率限制异常"""

    def __init__(
        self,
        message: str,
        provider: str = None,
        error_code: str = None,
        retry_after: int = None,
    ):
        super().__init__(message, provider, error_code)
        self.retry_after = retry_after


class LLMQuotaExceededError(LLMError):
    """LLM配额用尽异常"""

    pass


class LLMInvalidRequestError(LLMError):
    """LLM无效请求异常"""

    pass


class LLMAuthenticationError(LLMError):
    """LLM认证异常"""

    pass


class LLMNetworkError(LLMError):
    """LLM网络异常"""

    pass


class LLMModelNotFoundError(LLMError):
    """LLM模型未找到异常"""

    pass


class LLMTokenLimitError(LLMError):
    """LLM令牌限制异常"""

    pass


class LLMContentFilterError(LLMError):
    """LLM内容过滤异常"""

    pass


class LLMProviderUnavailableError(LLMError):
    """LLM提供者不可用异常"""

    pass
