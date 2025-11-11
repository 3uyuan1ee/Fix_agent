"""
Web搜索工具完整实现
包含数据模型、抽象基类、Tavily提供者、工厂类和主服务类
"""

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Union

from dotenv import load_dotenv
from langchain_core.tools import tool
from tavily import TavilyClient

# 加载环境变量
load_dotenv()


# ================================
# 数据模型
# ================================


@dataclass
class SearchResult:
    """标准化搜索结果项"""

    title: str
    url: str
    content: str
    score: float = 0.0
    source: str = ""
    published_date: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """字段验证"""
        if not self.title or not self.title.strip():
            raise ValueError("SearchResult.title 不能为空")
        if not self.url or not self.url.strip():
            raise ValueError("SearchResult.url 不能为空")
        if not self.content or not self.content.strip():
            raise ValueError("SearchResult.content 不能为空")
        if self.score < 0:
            raise ValueError("SearchResult.score 不能为负数")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "score": self.score,
            "source": self.source,
            "published_date": self.published_date,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchResult":
        """从字典创建实例"""
        return cls(**data)


@dataclass
class SearchResponse:
    """搜索响应"""

    success: bool
    results: List[SearchResult]
    query: str
    total: int
    provider: str
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """字段验证"""
        if not self.query or not self.query.strip():
            raise ValueError("SearchResponse.query 不能为空")
        if not self.provider or not self.provider.strip():
            raise ValueError("SearchResponse.provider 不能为空")
        if self.total < 0:
            raise ValueError("SearchResponse.total 不能为负数")
        if self.execution_time < 0:
            raise ValueError("SearchResponse.execution_time 不能为负数")
        if self.success and self.error:
            raise ValueError("成功的响应不能包含错误信息")
        if not self.success and not self.error:
            raise ValueError("失败的响应必须包含错误信息")

    def get_summary(self) -> Dict[str, Any]:
        """获取响应摘要"""
        return {
            "success": self.success,
            "query": self.query,
            "total_results": self.total,
            "provider": self.provider,
            "results_count": len(self.results),
            "execution_time": self.execution_time,
            "error": self.error,
            "has_results": len(self.results) > 0,
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "results": [result.to_dict() for result in self.results],
            "query": self.query,
            "total": self.total,
            "provider": self.provider,
            "error": self.error,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchResponse":
        """从字典创建实例"""
        # 转换results字段
        results_data = data.get("results", [])
        results = [SearchResult.from_dict(result_data) for result_data in results_data]

        # 创建副本避免修改原始数据
        data_copy = data.copy()
        data_copy["results"] = results

        return cls(**data_copy)


@dataclass
class SearchConfig:
    """搜索配置"""

    default_provider: str = "tavily"
    max_results: int = 5
    timeout: int = 30
    include_raw_content: bool = False
    retry_attempts: int = 3
    retry_delay: float = 1.0

    def __post_init__(self):
        """配置验证"""
        if self.max_results <= 0:
            raise ValueError("max_results 必须大于0")
        if self.timeout <= 0:
            raise ValueError("timeout 必须大于0")
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts 不能为负数")
        if self.retry_delay < 0:
            raise ValueError("retry_delay 不能为负数")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "default_provider": self.default_provider,
            "max_results": self.max_results,
            "timeout": self.timeout,
            "include_raw_content": self.include_raw_content,
            "retry_attempts": self.retry_attempts,
            "retry_delay": self.retry_delay,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchConfig":
        """从字典创建配置"""
        return cls(**data)


# ================================
# 异常类定义
# ================================


class SearchException(Exception):
    """搜索基础异常类"""

    pass


class ProviderNotFoundException(SearchException):
    """提供者未找到异常"""

    pass


class ConfigurationException(SearchException):
    """配置异常"""

    pass


class APIException(SearchException):
    """API调用异常"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class TimeoutException(SearchException):
    """超时异常"""

    pass


class RateLimitException(SearchException):
    """频率限制异常"""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


# ================================
# 抽象基类
# ================================


class BaseSearchProvider(ABC):
    """搜索提供者抽象基类"""

    def __init__(self, config: Optional[SearchConfig] = None, **kwargs):
        """
        初始化搜索提供者

        Args:
            config: 搜索配置
            **kwargs: 额外的配置参数
        """
        self.config = config or SearchConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup(**kwargs)

    def _setup(self, **kwargs):
        """
        子类特定的设置逻辑
        可被重写用于初始化子类特有的配置
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """获取提供者名称"""
        pass

    @abstractmethod
    def _check_availability(self) -> bool:
        """检查服务是否可用"""
        pass

    @abstractmethod
    def _build_search_params(self, query: str, **kwargs) -> Dict[str, Any]:
        """构建搜索参数"""
        pass

    @abstractmethod
    def _execute_search(self, params: Dict[str, Any]) -> Any:
        """执行搜索请求"""
        pass

    @abstractmethod
    def _parse_response(
        self, response: Any, query: str, execution_time: float
    ) -> SearchResponse:
        """解析搜索响应"""
        pass

    def _validate_query(self, query: str) -> None:
        """验证查询参数"""
        if not query or not query.strip():
            raise ConfigurationException("搜索查询不能为空")
        if len(query) > 1000:  # 基本的长度限制
            raise ConfigurationException("搜索查询长度不能超过1000个字符")

    def _prepare_search_kwargs(self, **kwargs) -> Dict[str, Any]:
        """准备搜索参数，合并配置和传入参数"""
        # 默认参数来自配置
        search_kwargs = {
            "max_results": self.config.max_results,
            "timeout": self.config.timeout,
            "include_raw_content": self.config.include_raw_content,
        }

        # 传入参数覆盖默认参数
        search_kwargs.update(kwargs)

        return search_kwargs

    def _retry_with_backoff(self, func, *args, **kwargs):
        """带退避的重试机制"""
        last_exception = None

        for attempt in range(self.config.retry_attempts + 1):
            try:
                return func(*args, **kwargs)
            except (APIException, TimeoutException) as e:
                last_exception = e

                # 如果是最后一次尝试，直接抛出异常
                if attempt == self.config.retry_attempts:
                    break

                # 如果是频率限制异常且有重试时间，使用指定时间
                if isinstance(e, RateLimitException) and e.retry_after:
                    delay = e.retry_after
                else:
                    # 指数退避
                    delay = self.config.retry_delay * (2**attempt)

                self.logger.warning(
                    f"搜索失败，{delay}秒后重试 (尝试 {attempt + 1}/{self.config.retry_attempts + 1}): {e}"
                )
                time.sleep(delay)

        raise last_exception

    def search(self, query: str, **kwargs) -> SearchResponse:
        """
        执行搜索的主方法

        Args:
            query: 搜索查询
            **kwargs: 额外的搜索参数

        Returns:
            SearchResponse: 搜索响应
        """
        start_time = time.time()

        try:
            # 验证查询
            self._validate_query(query)

            # 检查可用性
            if not self._check_availability():
                raise ConfigurationException(
                    f"搜索提供者 '{self.get_provider_name()}' 不可用"
                )

            # 准备参数
            search_kwargs = self._prepare_search_kwargs(**kwargs)
            search_params = self._build_search_params(query, **search_kwargs)

            self.logger.info(f"使用 {self.get_provider_name()} 搜索: {query[:50]}...")

            # 执行搜索（带重试）
            def do_search():
                return self._execute_search(search_params)

            raw_response = self._retry_with_backoff(do_search)

            # 计算执行时间
            execution_time = time.time() - start_time

            # 解析响应
            response = self._parse_response(raw_response, query, execution_time)

            self.logger.info(
                f"搜索完成，返回 {len(response.results)} 个结果，耗时 {execution_time:.2f}秒"
            )
            return response

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"搜索失败: {str(e)}"
            self.logger.error(error_msg)

            # 返回失败的响应，保持查询信息
            return SearchResponse(
                success=False,
                results=[],
                query=query if query else "invalid_query",
                total=0,
                provider=self.get_provider_name(),
                error=error_msg,
                execution_time=execution_time,
            )

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(provider={self.get_provider_name()})"

    def __repr__(self) -> str:
        return self.__str__()


class TavilyProvider(BaseSearchProvider):
    """Tavily搜索提供者"""

    def __init__(self, config: Optional[SearchConfig] = None, **kwargs):
        """
        初始化Tavily提供者

        Args:
            config: 搜索配置
            api_key: Tavily API密钥
            base_url: 自定义API端点
        """
        self.api_key = kwargs.get("api_key") or os.environ.get("TAVILY_API_KEY")
        self.base_url = kwargs.get("base_url") or os.environ.get("TAVILY_BASE_URL")

        if not self.api_key:
            raise ConfigurationException("TAVILY_API_KEY 环境变量未设置")

        super().__init__(config, **kwargs)

    def _setup(self, **kwargs):
        """设置Tavily客户端"""
        client_kwargs = {"api_key": self.api_key}

        if self.base_url and self.base_url.strip():
            client_kwargs["base_url"] = self.base_url.strip()

        self.client = TavilyClient(**client_kwargs)

    def get_provider_name(self) -> str:
        """获取提供者名称"""
        return "tavily"

    def _check_availability(self) -> bool:
        """检查Tavily服务是否可用"""
        try:
            # 简单的API调用来验证密钥和服务可用性
            self.client.search("test", max_results=1)
            return True
        except Exception as e:
            self.logger.warning(f"Tavily服务不可用: {e}")
            return False

    def _build_search_params(self, query: str, **kwargs) -> Dict[str, Any]:
        """构建Tavily搜索参数"""
        params = {
            "query": query,
            "max_results": kwargs.get("max_results", self.config.max_results),
            "include_raw_content": kwargs.get(
                "include_raw_content", self.config.include_raw_content
            ),
        }

        # 可选参数
        if "topic" in kwargs:
            params["topic"] = kwargs["topic"]
        if "search_depth" in kwargs:
            params["search_depth"] = kwargs["search_depth"]
        if "include_domains" in kwargs:
            params["include_domains"] = kwargs["include_domains"]
        if "exclude_domains" in kwargs:
            params["exclude_domains"] = kwargs["exclude_domains"]

        return params

    def _execute_search(self, params: Dict[str, Any]) -> Any:
        """执行Tavily搜索请求"""
        try:
            return self.client.search(**params)
        except Exception as e:
            # 根据异常类型转换为自定义异常
            error_msg = str(e).lower()

            if "timeout" in error_msg or "timed out" in error_msg:
                raise TimeoutException(f"Tavily API超时: {e}")
            elif "rate limit" in error_msg or "too many requests" in error_msg:
                # 尝试解析重试时间
                retry_after = None
                if "retry after" in error_msg:
                    import re

                    match = re.search(r"retry after (\d+)", error_msg)
                    if match:
                        retry_after = int(match.group(1))
                raise RateLimitException(f"Tavily API频率限制: {e}", retry_after)
            elif "unauthorized" in error_msg or "invalid api key" in error_msg:
                raise APIException(f"Tavily API密钥无效: {e}", 401)
            elif "not found" in error_msg or "invalid" in error_msg:
                raise APIException(f"Tavily API请求无效: {e}", 400)
            else:
                raise APIException(f"Tavily API调用失败: {e}")

    def _parse_response(
        self, response: Any, query: str, execution_time: float
    ) -> SearchResponse:
        """解析Tavily响应"""
        try:
            results = []
            for item in response.get("results", []):
                search_result = SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    score=item.get("score", 0.0),
                    source=self.get_provider_name(),
                    published_date=item.get("published_date"),
                    metadata={
                        "raw_content": item.get("raw_content"),
                        "score": item.get("score"),
                    },
                )
                results.append(search_result)

            return SearchResponse(
                success=True,
                results=results,
                query=query,
                total=len(results),
                provider=self.get_provider_name(),
                execution_time=execution_time,
                metadata={
                    "answer": response.get("answer"),
                    "follow_up_questions": response.get("follow_up_questions", []),
                },
            )

        except Exception as e:
            raise SearchException(f"解析Tavily响应失败: {e}")


class GoogleProvider(BaseSearchProvider):
    """Google搜索提供者（扩展示例）"""

    def get_provider_name(self) -> str:
        return "google"

    def _check_availability(self) -> bool:
        # 模拟实现
        return False  # 暂时返回False

    def _build_search_params(self, query: str, **kwargs) -> Dict[str, Any]:
        return {"query": query, **kwargs}

    def _execute_search(self, params: Dict[str, Any]) -> Any:
        raise NotImplementedError("Google提供者尚未实现")

    def _parse_response(
        self, response: Any, query: str, execution_time: float
    ) -> SearchResponse:
        raise NotImplementedError("Google提供者尚未实现")


class SearchProviderFactory:
    """搜索提供者工厂类"""

    _providers: Dict[str, Type[BaseSearchProvider]] = {
        "tavily": TavilyProvider,
        "google": GoogleProvider,
    }

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseSearchProvider]):
        """注册新的搜索提供者"""
        cls._providers[name.lower()] = provider_class

    @classmethod
    def create(
        cls, provider: str, config: Optional[SearchConfig] = None, **kwargs
    ) -> BaseSearchProvider:
        """
        创建搜索提供者实例

        Args:
            provider: 提供者名称
            config: 搜索配置
            **kwargs: 额外的配置参数

        Returns:
            BaseSearchProvider: 搜索提供者实例

        Raises:
            ProviderNotFoundException: 提供者未找到
        """
        provider_name = provider.lower()

        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ProviderNotFoundException(
                f"未知的搜索提供者: {provider}. 可用的提供者: {available}"
            )

        provider_class = cls._providers[provider_name]
        return provider_class(config=config, **kwargs)

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """获取可用的提供者列表"""
        return list(cls._providers.keys())


class WebSearchService:
    """Web搜索服务主类"""

    def __init__(
        self, provider: str = "tavily", config: Optional[SearchConfig] = None, **kwargs
    ):
        """
        初始化Web搜索服务

        Args:
            provider: 搜索提供者名称
            config: 搜索配置
            **kwargs: 传递给提供者的额外参数
        """
        self.provider = SearchProviderFactory.create(provider, config, **kwargs)

    def search(self, query: str, **kwargs) -> SearchResponse:
        """
        执行搜索

        Args:
            query: 搜索查询
            **kwargs: 搜索参数

        Returns:
            SearchResponse: 搜索响应
        """
        return self.provider.search(query, **kwargs)

    def get_provider_name(self) -> str:
        """获取当前提供者名称"""
        return self.provider.get_provider_name()


# 保持向后兼容的原始接口
class WebSearch:
    """
    原始WebSearch类的向后兼容包装器
    @deprecated: 建议使用WebSearchService
    """

    def __init__(self):
        import warnings

        warnings.warn(
            "WebSearch类已废弃，请使用WebSearchService类",
            DeprecationWarning,
            stacklevel=2,
        )

        # 创建默认的Tavily服务
        self.service = WebSearchService("tavily")

    def internet_search(
        self,
        query: str,
        max_results: int = 5,
        topic: str = "general",
        include_raw_content: bool = False,
        **kwargs,
    ):
        """
        兼容原始接口的搜索方法

        Args:
            query: 搜索查询
            max_results: 最大结果数
            topic: 搜索主题
            include_raw_content: 是否包含原始内容
            **kwargs: 其他参数

        Returns:
            搜索响应（保持原始格式兼容）
        """
        # 调用新的服务
        response = self.service.search(
            query=query,
            max_results=max_results,
            topic=topic,
            include_raw_content=include_raw_content,
            **kwargs,
        )

        # 转换为类似原始格式的响应
        if response.success:
            # 构造兼容原始格式的响应
            results = []
            for result in response.results:
                result_dict = {
                    "title": result.title,
                    "url": result.url,
                    "content": result.content,
                }
                if result.metadata.get("raw_content"):
                    result_dict["raw_content"] = result.metadata["raw_content"]
                results.append(result_dict)

            return {
                "results": results,
                "query": response.query,
                "answer": response.metadata.get("answer"),
                "follow_up_questions": response.metadata.get("follow_up_questions", []),
            }
        else:
            # 返回错误响应
            return {
                "error": response.error,
                "query": response.query,
            }


# 便捷函数，供agents调用
@tool(description="Web搜索工具，支持多种搜索引擎（默认使用Tavily）进行网络信息检索")
def search_web(query: str, provider: str = "tavily", **kwargs) -> str:
    """
    Web搜索主函数，供agents调用

    Args:
        query: 搜索查询
        provider: 搜索提供者
        **kwargs: 搜索参数

    Returns:
        搜索结果的JSON字符串
    """
    try:
        service = WebSearchService(provider=provider)
        response = service.search(query, **kwargs)
        return json.dumps(response.to_dict(), indent=2, ensure_ascii=False)
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "query": query,
            "results": [],
            "total": 0,
            "provider": provider,
        }
        return json.dumps(error_result, indent=2, ensure_ascii=False)
