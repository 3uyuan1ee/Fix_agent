"""CLI agent的自定义工具。"""

import os
from typing import Any, List, Literal, Optional

import dotenv
import requests
from langchain_core.tools import tool
from tavily import TavilyClient

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
        from .defect_aggregator import \
            aggregate_defects_tool as aggregate_defects
        from .multilang_code_analyzers import analyze_code_file as analyze_file

        # 第一步：执行代码静态分析
        analysis_result = analyze_file.invoke(
            {"file_path": file_path, "language": language}
        )

        # 解析分析结果
        try:
            analysis_data = json.loads(analysis_result)
            if not analysis_data.get("success", False):
                return json.dumps(
                    {
                        "success": False,
                        "error": f"代码分析失败: {analysis_data.get('error', '未知错误')}",
                        "file_path": file_path,
                    }
                )
        except json.JSONDecodeError:
            return json.dumps(
                {
                    "success": False,
                    "error": "代码分析结果格式错误",
                    "file_path": file_path,
                }
            )

        # 第二步：聚合和智能分析缺陷
        defects = analysis_data.get("detailed_result", {}).get("issues", [])
        if defects:
            aggregation_result = aggregate_defects.invoke(
                {"defects_json": json.dumps(defects)}
            )
            try:
                aggregation_data = json.loads(aggregation_result)
            except json.JSONDecodeError:
                # 如果聚合失败，返回基础分析结果
                aggregation_data = {
                    "success": True,
                    "result": {
                        "total_defects": len(defects),
                        "clusters": [],
                        "recommendations": ["缺陷聚合失败，请查看原始分析结果"],
                    },
                }
        else:
            # 没有发现缺陷
            aggregation_data = {
                "success": True,
                "result": {
                    "total_defects": 0,
                    "clusters": [],
                    "recommendations": ["代码质量良好，未发现需要修复的缺陷"],
                },
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
                "success": detailed_result.get("success", False),
            },
            "aggregation": aggregation_data.get("result", {}),
            "metadata": {
                "analysis_timestamp": detailed_result.get("metadata", {}).get(
                    "aggregation_timestamp", ""
                ),
                "toolchain_version": "1.0.0",
                "language_detected": detailed_result.get("language", "unknown"),
            },
        }

        return json.dumps(combined_result, indent=2, ensure_ascii=False)

    except ImportError as e:
        return json.dumps(
            {
                "success": False,
                "error": f"工具模块导入失败: {str(e)}",
                "file_path": file_path,
                "suggestion": "请确保multilang_code_analyzers.py和defect_aggregator.py模块可用",
            }
        )
    except json.JSONDecodeError as e:
        return json.dumps(
            {
                "success": False,
                "error": f"JSON解析错误: {str(e)}",
                "file_path": file_path,
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": f"工具链执行失败: {str(e)}",
                "file_path": file_path,
                "suggestion": "请检查文件路径是否正确，以及相关工具是否已安装",
            }
        )


@tool(
    description="编译项目并检测编译错误和警告。支持Python、JavaScript、Java、C/C++、Go、Rust等多种编程语言的编译检查。自动检测项目类型，使用相应的编译工具进行语法检查和编译验证，返回详细的错误和警告信息。"
)
def compile_project(project_path: str, build_config: Optional[str] = None) -> str:
    """
    编译项目并检测编译错误，提供给agent使用的一站式项目编译检查工具。

    此工具整合了多语言项目的编译检查功能：
    - 自动检测项目类型（Python、Node.js、Java、Go、C++、Rust等）
    - 执行相应语言的语法检查和编译验证
    - 识别编译错误、语法错误和警告信息
    - 提供详细的错误位置和修复建议
    - 支持自定义构建配置和超时设置

    Args:
        project_path: 项目根目录路径，支持相对路径和绝对路径
        build_config: 可选的构建配置JSON字符串，包含编译参数和设置

    Returns:
        编译检查结果的JSON字符串，包含：
            - success: 编译是否成功
            - project_type: 检测到的项目类型
            - compilation_result: 编译结果详情
                - success: 编译状态
                - errors: 错误列表，包含文件路径、错误类型、错误消息等
                - warnings: 警告列表
                - summary: 错误和警告统计信息
                - timestamp: 检查时间戳

    使用场景：
        - 代码提交前的编译检查
        - CI/CD流水线的质量门禁
        - 项目构建失败诊断
        - 多语言项目的统一编译检查
        - 语法错误快速定位

    工具优势：
        - 多语言统一接口，无需关心具体编译工具
        - 智能项目类型检测，自动选择合适的编译方式
        - 详细的错误定位和分类
        - 支持自定义构建配置，适应不同项目需求

    注意事项：
        - 需要系统中安装相应的编译工具
        - 大型项目编译可能需要较长时间
        - 建议在项目根目录执行
    """
    import json

    try:
        from .error_detector import compile_project as compile_project_impl

        # 调用原始实现
        result = compile_project_impl.invoke(
            {"project_path": project_path, "build_config": build_config}
        )

        # 确保返回有效的JSON格式
        try:
            parsed_result = json.loads(result)
            return json.dumps(parsed_result, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            return json.dumps(
                {"success": False, "error": "编译结果格式错误", "raw_result": result},
                indent=2,
                ensure_ascii=False,
            )

    except ImportError as e:
        return json.dumps(
            {
                "success": False,
                "error": f"编译模块导入失败: {str(e)}",
                "project_path": project_path,
                "suggestion": "请确保error_detector.py模块可用",
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": f"编译检查失败: {str(e)}",
                "project_path": project_path,
            },
            indent=2,
            ensure_ascii=False,
        )


@tool(
    description="运行项目并监控运行时错误。实时监控程序执行过程，捕获和分析运行时错误、异常和系统错误。支持自定义运行命令、超时设置和日志捕获。提供详细的错误堆栈跟踪和诊断信息。"
)
def run_and_monitor(
    project_path: str, run_command: str, timeout: int = 30, capture_logs: bool = True
) -> str:
    """
    运行项目并监控运行时错误，提供给agent使用的程序运行监控工具。

    此工具提供完整的程序运行监控功能：
    - 启动并监控程序执行过程
    - 实时捕获和分析运行时错误、异常和系统错误
    - 支持多种错误模式的识别和分类
    - 提供详细的错误堆栈跟踪和诊断信息
    - 可配置的超时控制和日志捕获功能

    Args:
        project_path: 项目根目录路径，程序执行的工作目录
        run_command: 要执行的具体命令（如"python main.py"、"npm start"等）
        timeout: 超时时间（秒），超过此时间将终止程序，默认30秒
        capture_logs: 是否捕获程序输出日志，默认为True

    Returns:
        运行监控结果的JSON字符串，包含：
            - success: 程序是否成功运行完成
            - runtime_result: 运行时监控详情
                - runtime_errors: 捕获的错误列表
                - output_log: 程序输出日志（如果启用）
                - exit_code: 程序退出码
                - timestamp: 运行时间戳

    使用场景：
        - 应用程序的运行时测试
        - 服务启动和健康检查
        - 长时间运行任务的监控
        - 脚本和工具的执行验证
        - 调试和故障诊断

    工具优势：
        - 实时错误监控，及时发现运行时问题
        - 智能错误分类，区分错误类型和严重程度
        - 完整的执行日志，便于问题排查
        - 灵活的超时控制，防止程序无限运行

    注意事项：
        - 运行命令需要在系统PATH中可访问
        - 长时间运行的程序建议设置合适的超时
        - 某些交互式程序可能无法正常监控
    """
    import json

    try:
        from .error_detector import run_and_monitor as run_and_monitor_impl

        # 调用原始实现
        result = run_and_monitor_impl.invoke(
            {
                "project_path": project_path,
                "run_command": run_command,
                "timeout": timeout,
                "capture_logs": capture_logs,
            }
        )

        # 确保返回有效的JSON格式
        try:
            parsed_result = json.loads(result)
            return json.dumps(parsed_result, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            return json.dumps(
                {
                    "success": False,
                    "error": "运行监控结果格式错误",
                    "raw_result": result,
                },
                indent=2,
                ensure_ascii=False,
            )

    except ImportError as e:
        return json.dumps(
            {
                "success": False,
                "error": f"运行监控模块导入失败: {str(e)}",
                "project_path": project_path,
                "suggestion": "请确保error_detector.py模块可用",
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": f"运行时监控失败: {str(e)}",
                "project_path": project_path,
            },
            indent=2,
            ensure_ascii=False,
        )


@tool(
    description="运行测试并捕获测试错误。支持多种测试框架（pytest、jest、junit、go test等），自动检测项目使用的测试框架，执行测试并捕获测试失败和错误信息。提供详细的测试结果和错误诊断。"
)
def run_tests_with_error_capture(
    project_path: str, test_framework: str = "auto"
) -> str:
    """
    运行测试并捕获测试错误，提供给agent使用的自动化测试执行工具。

    此工具提供完整的测试执行和错误捕获功能：
    - 自动检测项目使用的测试框架
    - 执行测试套件并收集测试结果
    - 捕获测试失败和错误信息
    - 支持多种测试框架和配置
    - 提供详细的测试报告和错误诊断

    Args:
        project_path: 项目根目录路径
        test_framework: 测试框架类型，可选值：
            - "auto": 自动检测（默认）
            - "pytest": Python pytest框架
            - "jest": JavaScript Jest框架
            - "junit": Java JUnit框架
            - "go_test": Go测试框架
            - 其他自定义框架

    Returns:
        测试执行结果的JSON字符串，包含：
            - success: 测试是否全部通过
            - test_framework: 使用的测试框架
            - test_result: 测试执行详情
                - success: 测试通过状态
                - test_errors: 捕获的测试错误列表
                - test_results: 测试结果统计
                - timestamp: 测试执行时间戳

    使用场景：
        - 自动化测试执行和验证
        - 持续集成流水线中的测试阶段
        - 测试失败的快速诊断
        - 多项目测试统一管理
        - 测试覆盖率分析辅助

    工具优势：
        - 智能测试框架检测，无需手动配置
        - 多测试框架统一接口
        - 详细的测试错误捕获和分析
        - 适合集成到自动化工作流中

    注意事项：
        - 需要项目中已配置相应的测试框架
        - 测试执行时间可能较长，建议设置合适的超时
        - 某些测试可能需要特定的环境依赖
    """
    import json

    try:
        from .error_detector import \
            run_tests_with_error_capture as run_tests_impl

        # 调用原始实现
        result = run_tests_impl.invoke(
            {"project_path": project_path, "test_framework": test_framework}
        )

        # 确保返回有效的JSON格式
        try:
            parsed_result = json.loads(result)
            return json.dumps(parsed_result, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            return json.dumps(
                {"success": False, "error": "测试结果格式错误", "raw_result": result},
                indent=2,
                ensure_ascii=False,
            )

    except ImportError as e:
        return json.dumps(
            {
                "success": False,
                "error": f"测试模块导入失败: {str(e)}",
                "project_path": project_path,
                "suggestion": "请确保error_detector.py模块可用",
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": f"测试执行失败: {str(e)}",
                "project_path": project_path,
            },
            indent=2,
            ensure_ascii=False,
        )


@tool(
    description="分析现有日志文件中的错误。智能搜索和分析项目中的日志文件，识别错误、异常和关键事件。支持多种日志格式和模式匹配，提供错误统计、分类和趋势分析。"
)
def analyze_existing_logs(
    project_path: str, log_patterns: Optional[List[str]] = None
) -> str:
    """
    分析现有日志文件中的错误，提供给agent使用的日志分析工具。

    此工具提供全面的日志错误分析功能：
    - 智能搜索和分析项目中的日志文件
    - 使用错误模式匹配识别异常和错误事件
    - 支持多种日志格式和编码处理
    - 提供错误统计、分类和趋势分析
    - 生成详细的分析报告和建议

    Args:
        project_path: 项目根目录路径，包含要分析的日志文件
        log_patterns: 可选的日志文件模式列表，用于指定要分析的日志文件
            - 默认模式：["*.log", "logs/*.log", "*.out", "*.err", "error.log"]
            - 支持glob模式，如"app/*.log", "**/*debug*"

    Returns:
        日志分析结果的JSON字符串，包含：
            - success: 分析是否成功完成
            - log_files_analyzed: 分析的日志文件数量
            - log_analysis: 日志分析详情
                - analyzed_files: 已分析的文件列表
                - total_errors: 发现的错误总数
                - errors: 错误详细信息（前50个）
                - error_summary: 错误统计和分类

    使用场景：
        - 生产环境日志分析和故障排查
        - 应用程序错误趋势分析
        - 系统健康检查和监控
        - 错误模式识别和预防
        - 运维团队的技术支持

    工具优势：
        - 智能错误识别，多种错误模式匹配
        - 支持多种日志格式和编码
        - 提供错误统计和趋势分析
        - 适合大量日志文件的批量分析

    注意事项：
        - 大型日志文件分析可能需要较长时间
        - 某些日志格式可能需要自定义模式
        - 敏感信息日志需要谨慎处理
    """
    import json

    try:
        from .error_detector import analyze_existing_logs as analyze_logs_impl

        # 调用原始实现
        result = analyze_logs_impl.invoke(
            {"project_path": project_path, "log_patterns": log_patterns}
        )

        # 确保返回有效的JSON格式
        try:
            parsed_result = json.loads(result)
            return json.dumps(parsed_result, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            return json.dumps(
                {
                    "success": False,
                    "error": "日志分析结果格式错误",
                    "raw_result": result,
                },
                indent=2,
                ensure_ascii=False,
            )

    except ImportError as e:
        return json.dumps(
            {
                "success": False,
                "error": f"日志分析模块导入失败: {str(e)}",
                "project_path": project_path,
                "suggestion": "请确保error_detector.py模块可用",
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": f"日志分析失败: {str(e)}",
                "project_path": project_path,
            },
            indent=2,
            ensure_ascii=False,
        )
