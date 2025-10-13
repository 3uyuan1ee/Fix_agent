"""
Pylint静态分析工具单元测试
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from src.tools.pylint_analyzer import PylintAnalyzer, PylintAnalysisError


class TestPylintAnalyzer:
    """Pylint分析器测试类"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.analyzer = PylintAnalyzer()

    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_analyze_valid_python_file(self):
        """测试分析有效的Python文件"""
        # 创建测试Python文件
        test_code = '''
def hello_world():
    """打印Hello World"""
    print("Hello, World!")

class TestClass:
    def __init__(self):
        self.value = 42

    def method(self):
        return self.value * 2
'''
        test_file = Path(self.temp_dir) / "test.py"
        test_file.write_text(test_code)

        # 分析文件
        result = self.analyzer.analyze_file(str(test_file))

        # 验证结果
        assert result is not None
        assert "file_path" in result
        assert "score" in result
        assert "issues" in result
        assert "messages" in result
        assert isinstance(result["score"], (int, float))
        assert isinstance(result["issues"], list)

    def test_analyze_file_with_issues(self):
        """测试分析有问题的文件"""
        # 创建有问题的Python文件
        test_code = '''
import unused_module
import sys

def function_with_issues():
    x=1+2
    y = x * 3
    return y

    # 未使用的变量
    unused_var = "not used"

class EmptyClass:
    pass

def function_without_docstring():
    pass
'''
        test_file = Path(self.temp_dir) / "issues.py"
        test_file.write_text(test_code)

        # 分析文件
        result = self.analyzer.analyze_file(str(test_file))

        # 验证结果
        assert result is not None
        assert len(result["issues"]) > 0

        # 验证问题类型
        issue_types = [issue.get("type") for issue in result["issues"]]
        assert any("warning" in t.lower() for t in issue_types) or any("error" in t.lower() for t in issue_types)

    def test_pylint_execution_timeout(self):
        """测试Pylint执行超时"""
        # 创建会导致长时间分析的文件
        test_code = '''
# 很长的复杂代码
def very_complex_function():
    result = []
    for i in range(1000):
        for j in range(1000):
            if i % 2 == 0 and j % 3 == 0:
                result.append(i * j)
            elif i % 5 == 0 or j % 7 == 0:
                result.append(i + j)
            else:
                result.append(i - j)
    return result

class VeryComplexClass:
    def __init__(self):
        self.data = [i for i in range(10000)]

    def complex_method(self):
        count = 0
        for item in self.data:
            if item % 2 == 0:
                if item % 3 == 0:
                    if item % 5 == 0:
                        count += 1
                    else:
                        count += 2
                else:
                    count += 3
            else:
                count += 1
        return count
'''
        test_file = Path(self.temp_dir) / "complex.py"
        test_file.write_text(test_code)

        # 用很短的超时时间测试
        analyzer = PylintAnalyzer(timeout=1)
        result = analyzer.analyze_file(str(test_file))

        # 应该返回超时错误或部分结果
        assert result is not None
        # 如果超时，应该有相应的错误信息
        if "error" in result:
            assert "timeout" in result["error"].lower()

    @patch('subprocess.run')
    def test_pylint_command_execution(self, mock_run):
        """测试Pylint命令执行"""
        # 模拟Pylint输出
        mock_result = MagicMock()
        mock_result.stdout = '''
{
    "messages": [
        {
            "type": "warning",
            "message": "Unused import sys",
            "message-id": "W0611",
            "symbol": "sys",
            "module": "test",
            "obj": "",
            "line": 1,
            "column": 0,
            "path": "/path/to/test.py"
        }
    ]
}
'''
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        test_file = Path(self.temp_dir) / "test.py"
        test_file.write_text("import sys\n")

        # 分析文件
        result = self.analyzer.analyze_file(str(test_file))

        # 验证subprocess被调用
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]  # 获取命令参数

        assert "pylint" in call_args
        assert str(test_file) in call_args

        # 验证结果
        assert result is not None

    @patch('subprocess.run')
    def test_pylint_not_installed(self, mock_run):
        """测试Pylint未安装的情况"""
        # 模拟Pylint未找到
        mock_run.side_effect = FileNotFoundError("pylint not found")

        test_file = Path(self.temp_dir) / "test.py"
        test_file.write_text("print('hello')")

        # 应该抛出异常
        with pytest.raises(PylintAnalysisError) as exc_info:
            self.analyzer.analyze_file(str(test_file))

        assert "pylint not found" in str(exc_info.value).lower() or "not installed" in str(exc_info.value).lower()

    def test_analyze_nonexistent_file(self):
        """测试分析不存在的文件"""
        with pytest.raises(PylintAnalysisError) as exc_info:
            self.analyzer.analyze_file("/nonexistent/file.py")

        assert "does not exist" in str(exc_info.value).lower()

    def test_analyze_non_python_file(self):
        """测试分析非Python文件"""
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("This is not Python code")

        with pytest.raises(PylintAnalysisError) as exc_info:
            self.analyzer.analyze_file(str(test_file))

        assert "not a python file" in str(exc_info.value).lower()

    def test_parse_pylint_score(self):
        """测试解析Pylint评分"""
        # 测试不同的评分格式
        test_cases = [
            ('10.00/10', 10.0),
            ('8.5/10', 8.5),
            ('Your code has been rated at 7.50/10', 7.50),
            ('Score: 9.25', 9.25)
        ]

        for score_text, expected_score in test_cases:
            with patch('subprocess.run') as mock_run:
                mock_result = MagicMock()
                mock_result.stdout = f'Report\n{score_text}\nMore text'
                mock_result.stderr = ""
                mock_result.returncode = 0
                mock_run.return_value = mock_result

                test_file = Path(self.temp_dir) / "test.py"
                test_file.write_text("print('test')")

                result = self.analyzer.analyze_file(str(test_file))
                assert abs(result["score"] - expected_score) < 0.01

    def test_custom_pylint_config(self):
        """测试使用自定义Pylint配置"""
        # 创建配置文件
        config_content = '''
[MASTER]
disable=C0114,C0115

[FORMAT]
max-line-length=120
'''
        config_file = Path(self.temp_dir) / ".pylintrc"
        config_file.write_text(config_content)

        test_file = Path(self.temp_dir) / "test.py"
        test_file.write_text("print('hello')")

        # 使用自定义配置的分析器
        analyzer = PylintAnalyzer(config_file=str(config_file))

        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = 'Score: 10.00/10'
            mock_result.stderr = ""
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            result = analyzer.analyze_file(str(test_file))

            # 验证配置文件参数被传递
            call_args = mock_run.call_args[0][0]
            assert any('--rcfile=' in arg for arg in call_args)

    def test_filter_issues_by_severity(self):
        """测试按严重程度过滤问题"""
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = '''[
    {
        "type": "fatal",
        "module": "test",
        "obj": "",
        "line": 1,
        "column": 0,
        "path": "/path/to/test.py",
        "symbol": "fatal-error",
        "message": "Fatal error",
        "message-id": "E0001"
    },
    {
        "type": "error",
        "module": "test",
        "obj": "",
        "line": 2,
        "column": 0,
        "path": "/path/to/test.py",
        "symbol": "error-symbol",
        "message": "Error message",
        "message-id": "E0002"
    },
    {
        "type": "warning",
        "module": "test",
        "obj": "",
        "line": 3,
        "column": 0,
        "path": "/path/to/test.py",
        "symbol": "warning-symbol",
        "message": "Warning message",
        "message-id": "W0001"
    },
    {
        "type": "convention",
        "module": "test",
        "obj": "",
        "line": 4,
        "column": 0,
        "path": "/path/to/test.py",
        "symbol": "convention-symbol",
        "message": "Convention message",
        "message-id": "C0001"
    }
]'''
            mock_result.stderr = ""
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            test_file = Path(self.temp_dir) / "test.py"
            test_file.write_text("print('test')")

            result = self.analyzer.analyze_file(str(test_file))

            # 验证所有问题都被收集
            assert len(result["issues"]) == 4

            # 验证问题信息完整
            for issue in result["issues"]:
                assert "type" in issue
                assert "message" in issue
                assert "line" in issue

    def test_get_analysis_summary(self):
        """测试获取分析摘要"""
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = '''Report
Your code has been rated at 8.50/10
[
    {
        "type": "warning",
        "module": "test",
        "obj": "",
        "line": 1,
        "column": 0,
        "path": "/path/to/test.py",
        "symbol": "warning-symbol",
        "message": "Warning message",
        "message-id": "W0001"
    }
]'''
            mock_result.stderr = ""
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            test_file = Path(self.temp_dir) / "test.py"
            test_file.write_text("print('test')")

            result = self.analyzer.analyze_file(str(test_file))
            summary = self.analyzer.get_analysis_summary(result)

            # 验证摘要信息
            assert "file_path" in summary
            assert "score" in summary
            assert "total_issues" in summary
            assert "issue_types" in summary
            assert summary["score"] == 8.5
            assert summary["total_issues"] == 1
            assert "warning" in summary["issue_types"]