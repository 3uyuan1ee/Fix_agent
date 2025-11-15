import os
from typing import Any, Literal

import dotenv
import requests
from langchain_core.tools import tool
from tavily import TavilyClient

dotenv.load_dotenv()

# 检查tavily api是否可用并创建服务
tavily_client = (
    TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
    if os.environ.get("TAVILY_API_KEY")
    else None
)


def http_request(
    url: str,
    method: str = "GET",
    headers: dict[str, str] = None,
    data: str | dict = None,
    params: dict[str, str] = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """向API和Web服务发起HTTP请求。

    Args:
        url: 目标URL
        method: HTTP方法 (GET, POST, PUT, DELETE等)
        headers: 要包含的HTTP头
        data: 请求体数据 (字符串或字典)
        params: URL查询参数
        timeout: 请求超时时间（秒）

    Returns:
        包含响应数据的字典，包括状态、头和内容
    """
    try:
        kwargs: dict[str, Any] = {
            "url": url,
            "method": method.upper(),
            "timeout": timeout,
        }

        if headers:
            kwargs["headers"] = headers
        if params:
            kwargs["params"] = params
        if data:
            if isinstance(data, dict):
                kwargs["json"] = data
            else:
                kwargs["data"] = data

        response = requests.request(**kwargs)

        try:
            content = response.json()
        except (ValueError, AttributeError):
            content = response.text

        return {
            "success": response.status_code < 400,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content": content,
            "url": response.url,
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "status_code": 0,
            "headers": {},
            "content": f"Request timed out after {timeout} seconds",
            "url": url,
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "status_code": 0,
            "headers": {},
            "content": f"Request error: {e!s}",
            "url": url,
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": 0,
            "headers": {},
            "content": f"Error making request: {e!s}",
            "url": url,
        }


def web_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """使用 Tavily 搜索网络以获取当前的信息和文档。
    此工具会搜索网络并返回相关结果。收到结果后，您必须将信息整合成自然、有用的回答提供给用户。
    Args：
    query：搜索查询（请具体详细）
    max_results：返回的结果数量（默认：5）
    topic：搜索主题类型 - "general"用于大多数查询，"news"用于当前事件
    include_raw_content：包含完整页面内容（注意：会使用更多token）
    Returns：
    包含以下内容的字典：
    - results：搜索结果列表，每个结果包含：
    - title：页面标题
    - url：页面 URL
    - content：页面的相关摘录
    - score：相关性得分（0 - 1）
    - query：原始搜索查询
    重要提示：使用此工具后：
    1. 阅读每个结果的"content"字段
    2. 提取回答用户问题的相关信息
    3. 将其综合为清晰、自然的语言回复
    4. 引用来源时提及页面标题或网址
    5. 绝不能向用户展示原始 JSON 数据 - 始终提供格式化的回复
    """
    if tavily_client is None:
        return {
            "error": "Tavily API key not configured. Please set TAVILY_API_KEY environment variable.",
            "query": query,
        }

    try:
        search_docs = tavily_client.search(
            query,
            max_results=max_results,
            include_raw_content=include_raw_content,
            topic=topic,
        )
        return search_docs
    except Exception as e:
        return {"error": f"Web search error: {e!s}", "query": query}
