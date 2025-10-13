"""
Flake8Analyzer单元测试
"""

import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.tools.flake8_analyzer import Flake8Analyzer, Flake8AnalysisError


class TestFlake8Analyzer:
    """Flake8Analyzer测试类"""

    def setup_method(self):
        """测试前的设置"""
        self.config_manager = Mock()
        self.config_manager.get_section.return_value = {
            'flake8': {
                'max_line_length': 88,
                'ignore_codes': ['E203', 'W503']
            }
        }
        self.analyzer = Flake8Analyzer(config_manager=self.config_manager)

    def test_init_default_config(self):
        """测试默认配置初始化"""
        analyzer = Flake8Analyzer()
        assert analyzer.max_line_length == 88
        assert analyzer.ignore_codes == ['E203', 'W503']
        assert analyzer.timeout == 30
        assert analyzer.default_config_file == '.flake8'

    def test_init_custom_config(self):
        """测试自定义配置初始化"""
        config_manager = Mock()
        config_manager.get_section.return_value = {
            'flake8': {
                'max_line_length': 100,
                'ignore_codes': ['E302', 'W291']
            }
        }
        analyzer = Flake8Analyzer(config_manager=config_manager, timeout=60)
        assert analyzer.max_line_length == 100
        assert analyzer.ignore_codes == ['E302', 'W291']
        assert analyzer.timeout == 60

    def test_build_flake8_command_basic(self):
        """测试构建基本flake8命令"""
        file_path = Path("test.py")
        cmd = self.analyzer._build_flake8_command(file_path)

        expected_cmd = [
            "flake8",
            "--max-line-length=88",
            "--ignore=E203,W503",
            "test.py"
        ]
        assert cmd == expected_cmd

    def test_build_flake8_command_with_config_file(self):
        """测试带配置文件的flake8命令构建"""
        config_file = ".custom_flake8"
        analyzer = Flake8Analyzer(
            config_manager=self.config_manager,
            config_file=config_file
        )

        with patch('pathlib.Path.exists', return_value=True):
            file_path = Path("test.py")
            cmd = analyzer._build_flake8_command(file_path)

            assert f"--config={config_file}" in cmd
            assert "test.py" in cmd

    def test_analyze_file_success(self, tmp_path):
        """测试成功分析文件"""
        # 创建测试文件
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')\n")

        # 模拟flake8输出
        mock_output = f"{test_file}:1:1: E302 expected 2 blank lines, found 1\n"
        mock_result = Mock()
        mock_result.stdout = mock_output
        mock_result.stderr = ""
        mock_result.returncode = 1

        with patch('subprocess.run', return_value=mock_result):
            result = self.analyzer.analyze_file(test_file)

            assert result["file_path"] == str(test_file)
            assert len(result["issues"]) == 1
            assert result["issues"][0]["code"] == "E302"
            assert result["issues"][0]["line"] == 1
            assert result["issues"][0]["column"] == 1
            assert "expected 2 blank lines" in result["issues"][0]["message"]

    def test_analyze_file_no_issues(self, tmp_path):
        """测试分析没有问题的文件"""
        # 创建测试文件
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')\n")

        # 模拟flake8输出（没有问题）
        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch('subprocess.run', return_value=mock_result):
            result = self.analyzer.analyze_file(test_file)

            assert result["file_path"] == str(test_file)
            assert len(result["issues"]) == 0
            assert result["return_code"] == 0

    def test_analyze_file_not_exists(self):
        """测试分析不存在的文件"""
        non_existent_file = Path("non_existent.py")

        with pytest.raises(Flake8AnalysisError, match="File does not exist"):
            self.analyzer.analyze_file(non_existent_file)

    def test_analyze_file_not_python(self, tmp_path):
        """测试分析非Python文件"""
        non_python_file = tmp_path / "test.txt"
        non_python_file.write_text("This is not a Python file")

        with pytest.raises(Flake8AnalysisError, match="File is not a Python file"):
            self.analyzer.analyze_file(non_python_file)

    def test_analyze_file_timeout(self, tmp_path):
        """测试分析超时"""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')\n")

        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("flake8", 30)):
            result = self.analyzer.analyze_file(test_file)

            assert result["file_path"] == str(test_file)
            assert result["error"] == "Analysis timeout"
            assert len(result["issues"]) == 0
            assert "Analysis timed out" in result["messages"]

    def test_analyze_file_flake8_not_installed(self, tmp_path):
        """测试flake8未安装"""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')\n")

        with patch('subprocess.run', side_effect=FileNotFoundError("flake8 not found")):
            with pytest.raises(Flake8AnalysisError, match="Flake8 is not installed"):
                self.analyzer.analyze_file(test_file)

    def test_parse_flake8_issues(self):
        """测试解析flake8问题输出"""
        output = "test.py:10:5: E302 expected 2 blank lines, found 1\n"
        output += "test.py:15:8: W291 trailing whitespace\n"

        file_path = Path("test.py")
        issues = self.analyzer._parse_flake8_issues(output, file_path)

        assert len(issues) == 2

        # 检查第一个问题
        issue1 = issues[0]
        assert issue1["line"] == 10
        assert issue1["column"] == 5
        assert issue1["code"] == "E302"
        assert issue1["severity"] == "error"
        assert issue1["type"] == "style"

        # 检查第二个问题
        issue2 = issues[1]
        assert issue2["line"] == 15
        assert issue2["column"] == 8
        assert issue2["code"] == "W291"
        assert issue2["severity"] == "warning"
        assert issue2["type"] == "warning"

    def test_parse_flake8_issues_invalid_format(self):
        """测试解析无效格式的输出"""
        output = "invalid output format\n"
        output += "test.py:10 E302 malformed line\n"

        file_path = Path("test.py")
        issues = self.analyzer._parse_flake8_issues(output, file_path)

        assert len(issues) == 0

    def test_get_severity_from_code(self):
        """测试根据代码获取严重程度"""
        assert self.analyzer._get_severity_from_code("E302") == "error"
        assert self.analyzer._get_severity_from_code("W291") == "warning"
        assert self.analyzer._get_severity_from_code("F401") == "error"
        assert self.analyzer._get_severity_from_code("C0111") == "info"
        assert self.analyzer._get_severity_from_code("N801") == "info"
        assert self.analyzer._get_severity_from_code("X123") == "warning"

    def test_get_type_from_code(self):
        """测试根据代码获取问题类型"""
        assert self.analyzer._get_type_from_code("E302") == "style"
        assert self.analyzer._get_type_from_code("W291") == "warning"
        assert self.analyzer._get_type_from_code("F401") == "fatal"
        assert self.analyzer._get_type_from_code("C0111") == "convention"
        assert self.analyzer._get_type_from_code("N801") == "naming"
        assert self.analyzer._get_type_from_code("X123") == "other"

    def test_get_analysis_summary(self):
        """测试获取分析摘要"""
        result = {
            "file_path": "test.py",
            "issues": [
                {"code": "E302", "severity": "error"},
                {"code": "W291", "severity": "warning"},
                {"code": "E303", "severity": "error"},
                {"code": "C0111", "severity": "info"}
            ],
            "return_code": 1,
            "messages": ["Some warning message"]
        }

        summary = self.analyzer.get_analysis_summary(result)

        assert summary["file_path"] == "test.py"
        assert summary["total_issues"] == 4
        assert summary["issue_types"]["error"] == 2
        assert summary["issue_types"]["warning"] == 1
        assert summary["issue_types"]["info"] == 1
        assert summary["issue_codes"]["E302"] == 1
        assert summary["issue_codes"]["W291"] == 1
        assert summary["has_errors"] is True
        assert summary["error_count"] == 2
        assert summary["return_code"] == 1
        assert summary["messages"] == ["Some warning message"]

    def test_get_analysis_summary_no_issues(self):
        """测试获取没有问题的分析摘要"""
        result = {
            "file_path": "test.py",
            "issues": [],
            "return_code": 0
        }

        summary = self.analyzer.get_analysis_summary(result)

        assert summary["total_issues"] == 0
        assert summary["issue_types"] == {}
        assert summary["issue_codes"] == {}
        assert summary["has_errors"] is False
        assert summary["error_count"] == 0
        assert summary["return_code"] == 0

    def test_parse_flake8_output_with_stderr(self, tmp_path):
        """测试解析包含stderr的输出"""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')\n")

        # 模拟flake8输出到stderr
        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.stderr = f"{test_file}:1:1: E302 expected 2 blank lines, found 1\n"
        mock_result.returncode = 1

        with patch('subprocess.run', return_value=mock_result):
            result = self.analyzer.analyze_file(test_file)

            assert len(result["issues"]) == 1
            assert result["issues"][0]["code"] == "E302"

    def test_parse_flake8_output_with_messages(self, tmp_path):
        """测试解析包含错误消息的输出"""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')\n")

        # 模拟flake8错误消息
        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.stderr = "flake8 configuration error"
        mock_result.returncode = 2

        with patch('subprocess.run', return_value=mock_result):
            result = self.analyzer.analyze_file(test_file)

            assert len(result["issues"]) == 0
            assert len(result["messages"]) > 0
            assert "configuration error" in result["messages"][0]