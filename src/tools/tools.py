"""CLI agent的自定义工具。"""

import os
from typing import Any, Literal, Optional

import requests
from tavily import TavilyClient
import dotenv
from langchain_core.tools import tool

dotenv.load_dotenv()

# Initialize Tavily client if API key is available
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
        kwargs: dict[str, Any] = {"url": url, "method": method.upper(), "timeout": timeout}

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


@tool(
    description="智能代码缺陷分析工具链，集成了代码静态分析和智能缺陷聚合功能。一键完成从代码分析到缺陷聚合的全流程，自动检测多语言代码问题，智能去重和聚类，提供优先级排序的缺陷报告。支持Python、JavaScript、Java、C/C++、Go、Rust等主流编程语言。"
)
def analyze_code_defects(file_path: str, language: Optional[str] = None) -> str:
    """
    智能代码缺陷分析工具链，提供给agent使用的一站式代码质量分析工具。

    此工具链整合了多语言静态代码分析和智能缺陷聚合两大核心功能：
    - 自动检测文件语言并选择合适的静态分析工具
    - 执行专业的代码质量分析，识别各种类型的缺陷
    - 智能聚合和去重相似的缺陷报告
    - 基于语义相似度对缺陷进行聚类
    - 分析缺陷根本原因并评估修复复杂度
    - 提供优先级排序和修复建议

    Args:
        file_path: 要分析的文件路径，支持相对路径和绝对路径
        language: 可选的语言标识符，如果不提供将自动检测
            支持的语言：python, javascript, java, cpp, go, rust等

    Returns:
        分析结果的JSON字符串，包含：
            - success: 分析是否成功
            - analysis: 原始代码分析结果
                - file_path: 分析的文件路径
                - language: 检测到的编程语言
                - tool_name: 使用的分析工具
                - issues: 发现的缺陷列表
                - score: 代码质量评分(0-100)
            - aggregation: 智能聚合分析结果
                - total_defects: 缺陷总数
                - deduplication_rate: 去重率
                - clusters: 缺陷聚类列表
                - priority_ranking: 优先级排序
                - recommendations: 修复建议
                - root_cause_analysis: 根因分析

    使用场景：
        - 代码审查前的质量检查
        - 重构前的现状分析
        - CI/CD流水线的质量门禁
        - 代码质量监控和改进
        - 技术债务评估

    工具链优势：
        - 一键式操作，无需多次调用不同工具
        - 智能语言检测，自动选择最适合的分析工具
        - 原始分析与智能聚合相结合，提供深度洞察
        - 统一的JSON输出格式，便于后续处理

    注意事项：
        - 需要系统中安装相应的静态分析工具(pylint, eslint等)
        - 分析大型文件可能需要较长时间
        - 建议在代码提交前执行分析
    """
    import json
    try:
        # 导入其他工具模块
        from .multilang_code_analyzers import analyze_code_file as analyze_file
        from .defect_aggregator import aggregate_defects_tool as aggregate_defects

        # 第一步：执行代码静态分析
        analysis_result = analyze_file.invoke({"file_path": file_path, "language": language})

        # 解析分析结果
        try:
            analysis_data = json.loads(analysis_result)
            if not analysis_data.get("success", False):
                return json.dumps({
                    "success": False,
                    "error": f"代码分析失败: {analysis_data.get('error', '未知错误')}",
                    "file_path": file_path
                })
        except json.JSONDecodeError:
            return json.dumps({
                "success": False,
                "error": "代码分析结果格式错误",
                "file_path": file_path
            })

        # 第二步：聚合和智能分析缺陷
        defects = analysis_data.get("detailed_result", {}).get("issues", [])
        if defects:
            aggregation_result = aggregate_defects.invoke({"defects_json": json.dumps(defects)})
            try:
                aggregation_data = json.loads(aggregation_result)
            except json.JSONDecodeError:
                # 如果聚合失败，返回基础分析结果
                aggregation_data = {
                    "success": True,
                    "result": {
                        "total_defects": len(defects),
                        "clusters": [],
                        "recommendations": ["缺陷聚合失败，请查看原始分析结果"]
                    }
                }
        else:
            # 没有发现缺陷
            aggregation_data = {
                "success": True,
                "result": {
                    "total_defects": 0,
                    "clusters": [],
                    "recommendations": ["代码质量良好，未发现需要修复的缺陷"]
                }
            }

        # 组合结果
        detailed_result = analysis_data.get("detailed_result", {})
        combined_result = {
            "success": True,
            "file_path": file_path,
            "analysis": {
                "file_path": detailed_result.get("file_path", file_path),
                "language": detailed_result.get("language", "unknown"),
                "tool_name": detailed_result.get("tool_name", "unknown"),
                "issues": defects,
                "score": detailed_result.get("score", 0),
                "execution_time": detailed_result.get("execution_time", 0),
                "success": detailed_result.get("success", False)
            },
            "aggregation": aggregation_data.get("result", {}),
            "metadata": {
                "analysis_timestamp": detailed_result.get("metadata", {}).get("aggregation_timestamp", ""),
                "toolchain_version": "1.0.0",
                "language_detected": detailed_result.get("language", "unknown")
            }
        }

        return json.dumps(combined_result, indent=2, ensure_ascii=False)

    except ImportError as e:
        return json.dumps({
            "success": False,
            "error": f"工具模块导入失败: {str(e)}",
            "file_path": file_path,
            "suggestion": "请确保multilang_code_analyzers.py和defect_aggregator.py模块可用"
        })
    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "error": f"JSON解析错误: {str(e)}",
            "file_path": file_path
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"工具链执行失败: {str(e)}",
            "file_path": file_path,
            "suggestion": "请检查文件路径是否正确，以及相关工具是否已安装"
        })
