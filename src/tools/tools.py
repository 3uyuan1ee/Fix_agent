"""统一的工具导出模块 - CLI agent的自定义工具总入口"""

import json
from typing import List, Optional

from langchain_core.tools import tool

from .defect_aggregator import aggregate_defects_tool as aggregate_defects
# 直接导入error_detector中的工具（已经是@tool装饰过的，避免双重包装）
from .error_detector import (analyze_existing_logs, compile_project,
                             run_and_monitor, run_tests_with_error_capture)
# 导入代码分析工具链模块
from .multilang_code_analyzers import analyze_code_file as analyze_file
# 导入网络工具
from .network_tools import http_request, web_search
# 导入代码格式化工具
from .professional_formatter import (batch_format_professional,
                                     format_code_professional)
# 导入project_explorer中的工具
from .project_explorer import (analyze_code_complexity,
                               explore_project_structure)
# 导入智能测试生成工具
from .test_generator import (execute_test_suite_tool,
                             generate_validation_tests_tool)


# 保持原有的analyze_code_defects工具链实现
@tool(
    description="""智能代码缺陷分析工具链，提供一站式代码质量检测服务。

核心功能：
- 自动检测编程语言并选择专业分析工具
- 执行多维度代码分析（语法、逻辑、安全、性能）
- 智能聚合和去重相似的缺陷报告
- 基于语义相似度进行缺陷聚类分析
- 评估修复复杂度和优先级排序
- 生成结构化的分析报告

支持语言：Python、JavaScript、Java、C/C++、Go、Rust、TypeScript等

使用场景：代码审查、重构前分析、CI/CD质量门禁、技术债务评估

输出：JSON格式的详细缺陷分析报告，包含问题定位、影响评估和修复建议"""
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
    try:
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


# 统一导出所有工具
__all__ = [
    # 网络工具
    "http_request",
    "web_search",
    # 代码分析工具链
    "analyze_code_defects",
    # 错误检测工具（直接从error_detector导入）
    "compile_project",
    "run_and_monitor",
    "run_tests_with_error_capture",
    "analyze_existing_logs",
    # 项目探索工具（从project_explorer导入）
    "explore_project_structure",
    "analyze_code_complexity",
    # 代码格式化工具（从professional_formatter导入）
    "format_code_professional",
    "batch_format_professional",
    # 智能测试工具（从test_generator导入）
    "generate_validation_tests_tool",
    "execute_test_suite_tool",
]

# 工具分类字典（便于管理和使用）
TOOL_CATEGORIES = {
    "网络工具": ["http_request", "web_search"],
    "代码分析": ["analyze_code_defects", "analyze_code_complexity"],
    "错误检测": [
        "compile_project",
        "run_and_monitor",
        "run_tests_with_error_capture",
        "analyze_existing_logs",
    ],
    "项目探索": ["explore_project_structure"],
    "代码格式化": ["format_code_professional", "batch_format_professional"],
    "测试生成": ["generate_validation_tests_tool", "execute_test_suite_tool"],
}


def get_all_tools():
    """获取所有可用工具的字典"""
    return {name: globals()[name] for name in __all__ if name in globals()}


def get_tools_by_category(category: str):
    """按分类获取工具"""
    if category not in TOOL_CATEGORIES:
        return {}

    tool_names = TOOL_CATEGORIES[category]
    return {name: globals()[name] for name in tool_names if name in globals()}
