"""
测试静态分析执行流程
"""

import pytest
import tempfile
from pathlib import Path

from src.tools.static_coordinator import StaticAnalysisCoordinator, SeverityLevel
from src.tools.report_generator import StaticAnalysisReportGenerator


class TestStaticAnalysisFlow:
    """测试静态分析执行流程"""

    @pytest.fixture
    def temp_project_dir(self):
        """临时项目目录fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "test_project"
            project_dir.mkdir()

            # 创建测试Python文件
            (project_dir / "good_code.py").write_text("""
def hello_world():
    \"\"\"简单的Hello World函数\"\"\"
    print("Hello, World!")
    return True

class GoodClass:
    def __init__(self):
        self.value = 42

    def method(self):
        return self.value * 2
            """)

            # 创建有问题的Python文件
            (project_dir / "bad_code.py").write_text("""
import os
import subprocess

def complex_function(a, b, c, d, e, f):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        if f:
                            return a + b + c + d + e + f

    # 未使用的变量
    unused_var = "this is not used"

    # 硬编码密码
    password = "secret123"

    # 过长的行
    very_long_line = "This is a very long line that exceeds the maximum line length limit and should be wrapped to multiple lines for better readability according to PEP8 standards"

    return None

# 缺少文档字符串
def no_docstring():
    x = 1
    return x

# 使用eval
eval('print("dangerous")')
            """)

            yield str(project_dir)

    @pytest.fixture
    def coordinator(self):
        """静态分析协调器fixture"""
        return StaticAnalysisCoordinator()

    @pytest.fixture
    def report_generator(self):
        """报告生成器fixture"""
        return StaticAnalysisReportGenerator()

    def test_coordinator_initialization(self, coordinator):
        """测试协调器初始化"""
        assert coordinator is not None
        assert hasattr(coordinator, 'execution_engine')
        assert hasattr(coordinator, 'enabled_tools')
        assert isinstance(coordinator.enabled_tools, list)
        assert len(coordinator.enabled_tools) > 0

    def test_analyze_single_file(self, coordinator, temp_project_dir):
        """测试分析单个文件"""
        good_file = Path(temp_project_dir) / "good_code.py"

        result = coordinator.analyze_file(str(good_file))

        assert result.file_path == str(good_file)
        assert result.execution_time > 0
        assert isinstance(result.issues, list)
        assert isinstance(result.tool_results, dict)
        assert isinstance(result.summary, dict)

    def test_analyze_multiple_files(self, coordinator, temp_project_dir):
        """测试分析多个文件"""
        files = [
            str(Path(temp_project_dir) / "good_code.py"),
            str(Path(temp_project_dir) / "bad_code.py")
        ]

        results = coordinator.analyze_files(files)

        assert len(results) == 2
        for result in results:
            assert result.file_path in files
            assert result.execution_time >= 0
            assert isinstance(result.issues, list)

    def test_enabled_tools_configuration(self, coordinator):
        """测试工具配置"""
        # 测试默认工具
        default_tools = coordinator.get_enabled_tools()
        assert 'ast' in default_tools
        assert 'pylint' in default_tools

        # 测试设置工具
        coordinator.set_enabled_tools(['ast', 'flake8'])
        updated_tools = coordinator.get_enabled_tools()
        assert 'ast' in updated_tools
        assert 'flake8' in updated_tools
        assert 'pylint' not in updated_tools

    def test_report_generator_initialization(self, report_generator):
        """测试报告生成器初始化"""
        assert report_generator is not None
        assert hasattr(report_generator, 'severity_weights')
        assert SeverityLevel.ERROR in report_generator.severity_weights

    def test_merge_results(self, report_generator, temp_project_dir, coordinator):
        """测试结果合并"""
        files = [
            str(Path(temp_project_dir) / "good_code.py"),
            str(Path(temp_project_dir) / "bad_code.py")
        ]

        results = coordinator.analyze_files(files)
        merged_result = report_generator.merge_results(results)

        assert merged_result.file_path == "multiple_files"
        assert len(merged_result.issues) >= 0
        assert merged_result.execution_time > 0

    def test_sort_issues(self, report_generator):
        """测试问题排序"""
        from src.tools.static_coordinator import AnalysisIssue

        issues = [
            AnalysisIssue("test", "file.py", 1, message="info issue", severity=SeverityLevel.INFO),
            AnalysisIssue("test", "file.py", 2, message="error issue", severity=SeverityLevel.ERROR),
            AnalysisIssue("test", "file.py", 3, message="warning issue", severity=SeverityLevel.WARNING),
        ]

        sorted_issues = report_generator.sort_issues(issues)

        # 错误应该排在最前面
        assert sorted_issues[0].severity == SeverityLevel.ERROR
        assert sorted_issues[1].severity == SeverityLevel.WARNING
        assert sorted_issues[2].severity == SeverityLevel.INFO

    def test_deduplicate_issues(self, report_generator):
        """测试问题去重"""
        from src.tools.static_coordinator import AnalysisIssue

        issues = [
            AnalysisIssue("test", "file.py", 1, message="duplicate issue", severity=SeverityLevel.WARNING),
            AnalysisIssue("test", "file.py", 1, message="duplicate issue", severity=SeverityLevel.WARNING),
            AnalysisIssue("test", "file.py", 2, message="unique issue", severity=SeverityLevel.INFO),
        ]

        unique_issues = report_generator.deduplicate_issues(issues)

        assert len(unique_issues) == 2
        assert unique_issues[0].message == "duplicate issue"
        assert unique_issues[1].message == "unique issue"

    def test_generate_json_report(self, report_generator, coordinator, temp_project_dir):
        """测试生成JSON格式报告"""
        files = [str(Path(temp_project_dir) / "bad_code.py")]
        results = coordinator.analyze_files(files)

        report = report_generator.generate_report(results, "json")

        assert "metadata" in report
        assert "summary" in report
        assert "issues" in report
        assert "file_details" in report
        assert "tool_details" in report

        # 验证元数据
        assert report["metadata"]["total_files"] == 1
        assert "generated_at" in report["metadata"]

        # 验证摘要
        assert "total_issues" in report["summary"]
        assert "severity_distribution" in report["summary"]

    def test_generate_summary_report(self, report_generator, coordinator, temp_project_dir):
        """测试生成摘要格式报告"""
        files = [str(Path(temp_project_dir) / "bad_code.py")]
        results = coordinator.analyze_files(files)

        report = report_generator.generate_report(results, "summary")

        # 摘要格式只包含metadata和summary
        assert "metadata" in report
        assert "summary" in report
        assert "issues" not in report  # 摘要格式不包含详细问题列表

    def test_save_report(self, report_generator, coordinator, temp_project_dir):
        """测试保存报告"""
        files = [str(Path(temp_project_dir) / "good_code.py")]
        results = coordinator.analyze_files(files)
        report = report_generator.generate_report(results, "json")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_report.json"

            success = report_generator.save_report(report, str(output_path))

            assert success is True
            assert output_path.exists()

            # 验证保存的文件内容
            import json
            with open(output_path, 'r', encoding='utf-8') as f:
                saved_report = json.load(f)

            assert "metadata" in saved_report
            assert saved_report["metadata"]["total_files"] == 1

    def test_end_to_end_flow(self, coordinator, report_generator, temp_project_dir):
        """测试端到端流程"""
        files = [
            str(Path(temp_project_dir) / "good_code.py"),
            str(Path(temp_project_dir) / "bad_code.py")
        ]

        # 1. 执行静态分析
        results = coordinator.analyze_files(files)
        assert len(results) == 2

        # 2. 生成报告
        report = report_generator.generate_report(results, "json")
        assert "summary" in report

        # 3. 验证报告内容
        assert report["metadata"]["total_files"] == 2
        assert report["metadata"]["tools_used"]  # 应该有使用的工具

        # 4. 保存报告
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "end_to_end_report.json"
            success = report_generator.save_report(report, str(output_path))
            assert success is True
            assert output_path.exists()

    def test_empty_results_handling(self, report_generator):
        """测试空结果处理"""
        empty_results = []

        merged_result = report_generator.merge_results(empty_results)
        assert merged_result.file_path == ""
        assert len(merged_result.issues) == 0

        report = report_generator.generate_report(empty_results, "json")
        assert report["metadata"]["total_files"] == 0
        assert report["summary"]["total_issues"] == 0

    def test_cleanup(self, coordinator):
        """测试资源清理"""
        # 验证协调器可以正常清理
        assert coordinator.execution_engine is not None
        coordinator.cleanup()
        # cleanup应该不会抛出异常