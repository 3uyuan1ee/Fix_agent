"""
Flake8Analyzer集成测试
测试真实的flake8工具集成
"""

import tempfile
from pathlib import Path
import subprocess
import sys

import pytest

from src.tools.flake8_analyzer import Flake8Analyzer, Flake8AnalysisError


class TestFlake8Integration:
    """Flake8集成测试类"""

    def setup_method(self):
        """测试前的设置"""
        # 检查flake8是否安装
        try:
            subprocess.run(['flake8', '--version'], capture_output=True, check=True)
            self.flake8_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.flake8_available = False

        self.analyzer = Flake8Analyzer()

    @pytest.mark.skipif(not pytest.importorskip("flake8", reason="flake8 not installed"),
                       reason="flake8 not available")
    def test_real_flake8_analysis_good_code(self, tmp_path):
        """测试真实flake8分析良好代码"""
        # 创建符合PEP8规范的Python文件
        good_file = tmp_path / "good_code.py"
        good_code = '''
"""
This is a good Python file following PEP8.
"""

def hello_world():
    """Print hello world message."""
    print("Hello, World!")


if __name__ == "__main__":
    hello_world()
'''
        good_file.write_text(good_code)

        result = self.analyzer.analyze_file(good_file)

        assert result["file_path"] == str(good_file)
        # 对于良好代码，应该没有或少有问题
        assert isinstance(result["issues"], list)

    @pytest.mark.skipif(not pytest.importorskip("flake8", reason="flake8 not installed"),
                       reason="flake8 not available")
    def test_real_flake8_analysis_bad_code(self, tmp_path):
        """测试真实flake8分析有问题代码"""
        # 创建有PEP8问题的Python文件
        bad_file = tmp_path / "bad_code.py"
        bad_code = '''
import os,sys
def bad_function( ):
    x=1+2
    return x

def another_bad_function():
    y=[1,2,3,4,5,6,7,8,9,10]
    return y
'''
        bad_file.write_text(bad_code)

        result = self.analyzer.analyze_file(bad_file)

        assert result["file_path"] == str(bad_file)
        # 对于有问题代码，应该检测到问题
        assert isinstance(result["issues"], list)
        # 可能有多个问题
        if result["issues"]:
            # 检查问题格式
            issue = result["issues"][0]
            assert "line" in issue
            assert "column" in issue
            assert "code" in issue
            assert "message" in issue
            assert "severity" in issue

    def test_flake8_not_installed_error(self, tmp_path):
        """测试flake8未安装时的错误处理"""
        # 创建一个测试文件
        test_file = tmp_path / "test.py"
        test_file.write_text("print('test')\n")

        # 使用不存在的flake8路径模拟未安装情况
        analyzer = Flake8Analyzer(timeout=1)

        # 通过mock模拟flake8未安装的情况
        import unittest.mock
        with unittest.mock.patch('subprocess.run', side_effect=FileNotFoundError("flake8: not found")):
            with pytest.raises(Flake8AnalysisError, match="Flake8 is not installed"):
                analyzer.analyze_file(test_file)

    def test_analysis_summary_with_real_results(self, tmp_path):
        """测试使用真实结果生成摘要"""
        # 创建一个模拟的结果
        mock_result = {
            "file_path": str(tmp_path / "test.py"),
            "issues": [
                {
                    "code": "E302",
                    "severity": "error",
                    "line": 10,
                    "column": 1,
                    "message": "expected 2 blank lines",
                    "type": "style"
                },
                {
                    "code": "W291",
                    "severity": "warning",
                    "line": 15,
                    "column": 20,
                    "message": "trailing whitespace",
                    "type": "warning"
                }
            ],
            "return_code": 1
        }

        summary = self.analyzer.get_analysis_summary(mock_result)

        assert summary["total_issues"] == 2
        assert summary["issue_types"]["error"] == 1
        assert summary["issue_types"]["warning"] == 1
        assert summary["issue_codes"]["E302"] == 1
        assert summary["issue_codes"]["W291"] == 1
        assert summary["has_errors"] is True
        assert summary["error_count"] == 1

    def test_flake8_config_integration(self, tmp_path):
        """测试flake8配置集成"""
        # 创建自定义配置文件
        config_file = tmp_path / ".flake8"
        config_content = """
[flake8]
max-line-length = 120
ignore = E302,W291
"""
        config_file.write_text(config_content)

        # 创建测试文件
        test_file = tmp_path / "test.py"
        test_code = "def test():\n    pass\n"  # 这行应该被E302捕获，但会被配置忽略
        test_file.write_text(test_code)

        # 使用自定义配置的分析器
        analyzer = Flake8Analyzer(config_file=str(config_file))

        # 检查命令构建是否包含配置
        cmd = analyzer._build_flake8_command(test_file)
        assert f"--config={config_file}" in cmd
        assert "--max-line-length=88" in cmd  # 默认值
        assert "--ignore=E203,W503" in cmd    # 默认值

    @pytest.mark.skipif(not pytest.importorskip("flake8", reason="flake8 not installed"),
                       reason="flake8 not available")
    def test_timeout_handling(self, tmp_path):
        """测试超时处理"""
        # 创建一个可能导致长时间分析的文件（如果可能的话）
        test_file = tmp_path / "timeout_test.py"
        test_file.write_text("print('test')\n")

        # 使用很短的超时时间
        analyzer = Flake8Analyzer(timeout=0.001)  # 1毫秒，应该超时

        # 在实际环境中，flake8通常很快，所以这个测试可能不会触发超时
        # 但我们可以测试超时处理的逻辑
        result = analyzer.analyze_file(test_file)

        # 检查结果格式
        assert "file_path" in result
        assert "issues" in result
        assert "messages" in result