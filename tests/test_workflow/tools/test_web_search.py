"""
Web搜索工具单元测试
"""

import json
import unittest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import asdict

from web_search import (
    SearchResult,
    SearchResponse,
    SearchConfig,
    BaseSearchProvider,
    SearchException,
    ConfigurationException,
    APIException,
    TimeoutException,
    RateLimitException,
    ProviderNotFoundException,
    TavilyProvider,
    GoogleProvider,
    SearchProviderFactory,
    WebSearchService,
    WebSearch,
    search_web
)


class TestSearchModels(unittest.TestCase):
    """测试数据模型"""

    def test_search_result_creation(self):
        """测试SearchResult创建"""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            content="Test content"
        )
        self.assertEqual(result.title, "Test Title")
        self.assertEqual(result.url, "https://example.com")
        self.assertEqual(result.content, "Test content")
        self.assertEqual(result.score, 0.0)

    def test_search_result_validation(self):
        """测试SearchResult验证"""
        # 测试空标题
        with self.assertRaises(ValueError):
            SearchResult(title="", url="https://example.com", content="content")

        # 测试空URL
        with self.assertRaises(ValueError):
            SearchResult(title="title", url="", content="content")

        # 测试负分
        with self.assertRaises(ValueError):
            SearchResult(title="title", url="https://example.com", content="content", score=-1.0)

    def test_search_response_creation(self):
        """测试SearchResponse创建"""
        result = SearchResult(title="Test", url="https://test.com", content="Test")
        response = SearchResponse(
            success=True,
            results=[result],
            query="test query",
            total=1,
            provider="test"
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.results), 1)
        self.assertEqual(response.query, "test query")

    def test_search_response_validation(self):
        """测试SearchResponse验证"""
        result = SearchResult(title="Test", url="https://test.com", content="Test")

        # 测试成功但有错误
        with self.assertRaises(ValueError):
            SearchResponse(
                success=True,
                results=[result],
                query="test",
                total=1,
                provider="test",
                error="error"
            )

        # 测试失败但没有错误
        with self.assertRaises(ValueError):
            SearchResponse(
                success=False,
                results=[],
                query="test",
                total=0,
                provider="test"
            )

    def test_search_config_creation(self):
        """测试SearchConfig创建"""
        config = SearchConfig(max_results=10, timeout=60)
        self.assertEqual(config.max_results, 10)
        self.assertEqual(config.timeout, 60)

    def test_to_dict_from_dict(self):
        """测试序列化和反序列化"""
        # 测试SearchResult
        result = SearchResult(title="Test", url="https://test.com", content="Test")
        result_dict = result.to_dict()
        result_restored = SearchResult.from_dict(result_dict)
        self.assertEqual(result.title, result_restored.title)

        # 测试SearchResponse
        response = SearchResponse(
            success=True,
            results=[result],
            query="test",
            total=1,
            provider="test"
        )
        response_dict = response.to_dict()
        response_restored = SearchResponse.from_dict(response_dict)
        self.assertEqual(response.query, response_restored.query)


class MockSearchProvider(BaseSearchProvider):
    """用于测试的模拟搜索提供者"""

    def get_provider_name(self) -> str:
        return "mock"

    def _check_availability(self) -> bool:
        return True

    def _build_search_params(self, query: str, **kwargs) -> dict:
        return {"query": query, **kwargs}

    def _execute_search(self, params: dict):
        return {"results": [{"title": "Mock Result", "url": "https://mock.com", "content": "Mock content"}]}

    def _parse_response(self, response: any, query: str, execution_time: float) -> SearchResponse:
        result = SearchResult(
            title="Mock Result",
            url="https://mock.com",
            content="Mock content"
        )
        return SearchResponse(
            success=True,
            results=[result],
            query=query,
            total=1,
            provider=self.get_provider_name(),
            execution_time=execution_time
        )


class TestBaseSearchProvider(unittest.TestCase):
    """测试搜索提供者基类"""

    def setUp(self):
        self.provider = MockSearchProvider()

    def test_provider_initialization(self):
        """测试提供者初始化"""
        config = SearchConfig(max_results=10)
        provider = MockSearchProvider(config)
        self.assertEqual(provider.config.max_results, 10)

    def test_query_validation(self):
        """测试查询验证"""
        # 测试空查询 - 现在返回失败的响应而不是抛出异常
        response = self.provider.search("")
        self.assertFalse(response.success)
        self.assertIn("不能为空", response.error)

        # 测试过长查询 - 现在返回失败的响应而不是抛出异常
        response = self.provider.search("a" * 1001)
        self.assertFalse(response.success)
        self.assertIn("不能超过1000", response.error)

    def test_search_success(self):
        """测试成功搜索"""
        response = self.provider.search("test query")
        self.assertTrue(response.success)
        self.assertEqual(response.query, "test query")
        self.assertEqual(len(response.results), 1)

    def test_search_failure(self):
        """测试搜索失败"""
        # 重写_execute_search来模拟失败
        def fail_execute(params):
            raise APIException("API Error")

        original_execute = self.provider._execute_search
        self.provider._execute_search = fail_execute

        response = self.provider.search("test query")
        self.assertFalse(response.success)
        self.assertIsNotNone(response.error)

        # 恢复原方法
        self.provider._execute_search = original_execute


class TestTavilyProvider(unittest.TestCase):
    """测试Tavily提供者"""

    @patch.dict('os.environ', {'TAVILY_API_KEY': 'test_key'})
    def setUp(self):
        with patch('web_search.TavilyClient'):
            self.provider = TavilyProvider()

    def test_provider_name(self):
        """测试提供者名称"""
        self.assertEqual(self.provider.get_provider_name(), "tavily")

    def test_missing_api_key(self):
        """测试缺少API密钥"""
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(ConfigurationException):
                TavilyProvider()

    @patch.dict('os.environ', {'TAVILY_API_KEY': 'test_key'})
    def test_build_search_params(self):
        """测试构建搜索参数"""
        params = self.provider._build_search_params(
            "test query",
            max_results=10,
            topic="news"
        )
        self.assertEqual(params["query"], "test query")
        self.assertEqual(params["max_results"], 10)
        self.assertEqual(params["topic"], "news")

    @patch.dict('os.environ', {'TAVILY_API_KEY': 'test_key'})
    def test_parse_response(self):
        """测试解析响应"""
        mock_response = {
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://test.com",
                    "content": "Test content",
                    "score": 0.9
                }
            ],
            "answer": "Test answer"
        }

        response = self.provider._parse_response(mock_response, "test query", 1.0)

        self.assertTrue(response.success)
        self.assertEqual(len(response.results), 1)
        self.assertEqual(response.results[0].title, "Test Result")
        self.assertEqual(response.metadata["answer"], "Test answer")

    @patch.dict('os.environ', {'TAVILY_API_KEY': 'test_key'})
    def test_execute_search_exceptions(self):
        """测试执行搜索异常处理"""
        # 模拟超时异常
        self.provider.client.search.side_effect = Exception("timeout occurred")

        with self.assertRaises(TimeoutException):
            self.provider._execute_search({"query": "test"})

        # 模拟频率限制异常
        self.provider.client.search.side_effect = Exception("rate limit exceeded")

        with self.assertRaises(RateLimitException):
            self.provider._execute_search({"query": "test"})


class TestSearchProviderFactory(unittest.TestCase):
    """测试搜索提供者工厂"""

    def test_create_tavily_provider(self):
        """测试创建Tavily提供者"""
        with patch.dict('os.environ', {'TAVILY_API_KEY': 'test_key'}):
            with patch('web_search.TavilyClient'):
                provider = SearchProviderFactory.create("tavily")
                self.assertIsInstance(provider, TavilyProvider)

    def test_create_google_provider(self):
        """测试创建Google提供者"""
        provider = SearchProviderFactory.create("google")
        self.assertIsInstance(provider, GoogleProvider)

    def test_unknown_provider(self):
        """测试未知提供者"""
        with self.assertRaises(ProviderNotFoundException):
            SearchProviderFactory.create("unknown")

    def test_get_available_providers(self):
        """测试获取可用提供者"""
        providers = SearchProviderFactory.get_available_providers()
        self.assertIn("tavily", providers)
        self.assertIn("google", providers)

    def test_register_provider(self):
        """测试注册新提供者"""
        SearchProviderFactory.register_provider("mock", MockSearchProvider)
        provider = SearchProviderFactory.create("mock")
        self.assertIsInstance(provider, MockSearchProvider)


class TestWebSearchService(unittest.TestCase):
    """测试Web搜索服务"""

    @patch.dict('os.environ', {'TAVILY_API_KEY': 'test_key'})
    def setUp(self):
        with patch('web_search.TavilyClient'):
            self.service = WebSearchService()

    def test_service_initialization(self):
        """测试服务初始化"""
        self.assertIsNotNone(self.service.provider)
        self.assertEqual(self.service.get_provider_name(), "tavily")

    @patch.dict('os.environ', {'TAVILY_API_KEY': 'test_key'})
    def test_search_with_custom_provider(self):
        """测试使用自定义提供者搜索"""
        service = WebSearchService("mock")
        self.assertEqual(service.get_provider_name(), "mock")

    @patch.dict('os.environ', {'TAVILY_API_KEY': 'test_key'})
    def test_search_method(self):
        """测试搜索方法"""
        # 使用mock提供者进行测试
        service = WebSearchService("mock")
        response = service.search("test query")
        self.assertTrue(response.success)


class TestBackwardCompatibility(unittest.TestCase):
    """测试向后兼容性"""

    @patch.dict('os.environ', {'TAVILY_API_KEY': 'test_key'})
    def test_original_websearch_class(self):
        """测试原始WebSearch类"""
        with patch('web_search.TavilyClient'):
            with self.assertWarns(DeprecationWarning):
                web_search = WebSearch()
                self.assertIsNotNone(web_search.service)

    @patch.dict('os.environ', {'TAVILY_API_KEY': 'test_key'})
    def test_internet_search_compatibility(self):
        """测试internet_search方法兼容性"""
        with patch('web_search.TavilyClient') as mock_client:
            # 模拟Tavily响应
            mock_client.return_value.search.return_value = {
                "results": [
                    {
                        "title": "Test Result",
                        "url": "https://test.com",
                        "content": "Test content"
                    }
                ],
                "query": "test query",
                "answer": "Test answer"
            }

            web_search = WebSearch()
            result = web_search.internet_search("test query")

            self.assertIn("results", result)
            self.assertIn("query", result)
            self.assertEqual(len(result["results"]), 1)


class TestConvenienceFunction(unittest.TestCase):
    """测试便捷函数"""

    def test_search_web_function(self):
        """测试search_web函数"""
        result = search_web("test query", provider="mock")
        self.assertTrue(result["success"])
        self.assertEqual(result["query"], "test query")
        self.assertEqual(result["provider"], "mock")

    def test_search_web_with_error(self):
        """测试search_web函数错误处理"""
        result = search_web("test query", provider="unknown")
        self.assertFalse(result["success"])
        self.assertIn("error", result)


if __name__ == '__main__':
    unittest.main()