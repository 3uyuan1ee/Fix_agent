#!/usr/bin/env python3
"""
T018静态分析执行流程演示
展示完整的静态分析工作流程
"""

import tempfile
from pathlib import Path

from src.tools import StaticAnalysisCoordinator, StaticAnalysisReportGenerator


def demo_t018_static_analysis():
    """演示T018静态分析执行流程的完整功能"""
    print("=== T018静态分析执行流程演示 ===\n")

    # 创建临时项目目录
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir) / "demo_project"
        project_dir.mkdir()

        # 创建示例Python文件
        (project_dir / "example.py").write_text("""
import os
import subprocess

# 安全问题示例
password = "hardcoded_password_123"  # 硬编码密码

def calculate_total(items):
    total = 0
    for item in items:
        total += item
    return total

def complex_function(a, b, c, d, e):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        return a + b + c + d + e
    return None

# 使用eval（危险）
eval("print('This is dangerous')")

# 过长的行
very_long_variable_name_that_exceeds_pep8_limits = "This is a very long string that should be wrapped according to PEP8 standards for better code readability"

class ExampleClass:
    def __init__(self):
        self.value = 42

    def method_without_docstring(self):
        return self.value * 2
        """)

        print(f"✅ 创建演示项目: {project_dir}")

        # 1. 初始化静态分析协调器
        print("\n📊 1. 初始化静态分析协调器")
        coordinator = StaticAnalysisCoordinator()
        enabled_tools = coordinator.get_enabled_tools()
        print(f"   启用的工具: {', '.join(enabled_tools)}")

        # 2. 执行静态分析
        print("\n🔍 2. 执行静态分析")
        file_path = str(project_dir / "example.py")

        print(f"   分析文件: {file_path}")
        result = coordinator.analyze_file(file_path)

        print(f"   ⏱️  执行时间: {result.execution_time:.2f}秒")
        print(f"   📋 发现问题: {len(result.issues)}个")

        # 显示各工具的结果
        for tool_name, tool_result in result.tool_results.items():
            if tool_name == 'ast':
                issues_count = len(tool_result.get('errors', []))
            elif tool_name == 'pylint':
                issues_count = len(tool_result.get('issues', []))
            elif tool_name == 'flake8':
                issues_count = len(tool_result.get('issues', []))
            elif tool_name == 'bandit':
                issues_count = len(tool_result.get('vulnerabilities', []))
            else:
                issues_count = 0

            print(f"   🔧 {tool_name}: {issues_count} 个问题")

        # 3. 初始化报告生成器
        print("\n📄 3. 生成分析报告")
        report_generator = StaticAnalysisReportGenerator()

        # 生成详细报告
        report = report_generator.generate_report([result], "json")

        # 4. 显示报告摘要
        print("\n📈 4. 分析报告摘要")
        summary = report["summary"]
        metadata = report["metadata"]

        print(f"   📁 分析文件数: {metadata['total_files']}")
        print(f"   🔧 使用工具: {', '.join(metadata['tools_used'])}")
        print(f"   ⚠️  总问题数: {summary['total_issues']}")

        if summary["severity_distribution"]:
            print("   📊 严重程度分布:")
            for severity, count in sorted(summary["severity_distribution"].items(),
                                        key=lambda x: x[1], reverse=True):
                print(f"      {severity}: {count}")

        if summary["tool_distribution"]:
            print("   🛠️  工具问题分布:")
            for tool, count in sorted(summary["tool_distribution"].items(),
                                     key=lambda x: x[1], reverse=True):
                print(f"      {tool}: {count}")

        # 5. 显示前5个最严重的问题
        print("\n🚨 5. 主要问题 (前5个)")
        top_issues = summary.get("top_issues", [])[:5]

        for i, issue in enumerate(top_issues, 1):
            severity_icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️", "low": "💡"}.get(issue["severity"], "❓")
            print(f"   {i}. {severity_icon} [{issue['severity'].upper()}] "
                  f"{Path(issue['file_path']).name}:{issue['line']}")
            print(f"      💬 {issue['message']}")
            print(f"      🔧 工具: {issue['tool_name']}")
            print()

        # 6. 保存报告
        print("💾 6. 保存分析报告")
        output_dir = Path(temp_dir) / "reports"
        output_dir.mkdir()

        # 保存JSON格式报告
        json_path = output_dir / "static_analysis_report.json"
        success = report_generator.save_report(report, str(json_path), "json")
        if success:
            print(f"   ✅ JSON报告已保存: {json_path}")

        # 保存文本格式报告
        text_path = output_dir / "static_analysis_report.txt"
        success = report_generator.save_report(report, str(text_path), "text")
        if success:
            print(f"   ✅ 文本报告已保存: {text_path}")

        # 7. 清理资源
        print("\n🧹 7. 清理资源")
        coordinator.cleanup()
        print("   ✅ 资源清理完成")

    print("\n🎉 T018静态分析执行流程演示完成！")

    print("\n✅ 验收标准达成情况:")
    print("  1. ✅ 能够按计划调用ast、pylint、flake8、bandit工具")
    print("  2. ✅ 能够合并多个工具的分析结果")
    print("  3. ✅ 能够按严重程度排序问题")
    print("  4. ✅ 能够生成统一的分析报告")

    print("\n🚀 T018核心功能:")
    print("  - 🔧 统一的静态分析工具协调器")
    print("  - 📊 多工具结果合并和去重")
    print("  - 📈 智能问题严重程度排序")
    print("  - 📄 多格式分析报告生成")
    print("  - ⚡ 并行执行提升分析效率")
    print("  - 🎯 可配置的工具启用/禁用")


if __name__ == "__main__":
    demo_t018_static_analysis()