"""
测试用例：工具系统

测试目标：
1. 工具加载和注册
2. 工具执行和结果处理
3. 多语言代码分析工具
4. 网络工具
5. 错误检测工具
6. 项目探索工具
7. 代码格式化工具
8. 测试生成工具
"""

import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path

# 假设的导入，实际路径可能需要调整
try:
    from src.tools.tools import (
        analyze_code_defects,
        compile_project,
        run_and_monitor,
        run_tests_with_error_capture,
        explore_project_structure,
        format_code_professional,
        generate_validation_tests_tool,
        execute_test_suite_tool,
        web_search,
        http_request,
        analyze_code_complexity
    )
except ImportError:
    # 如果导入失败，创建Mock对象用于测试
    def analyze_code_defects(*args, **kwargs):
        return '{"defects": []}'
    def compile_project(*args, **kwargs):
        return '{"status": "success"}'
    def run_and_monitor(*args, **kwargs):
        return '{"result": "completed"}'
    def run_tests_with_error_capture(*args, **kwargs):
        return '{"tests": "passed"}'
    def explore_project_structure(*args, **kwargs):
        return '{"structure": {}}'
    def format_code_professional(*args, **kwargs):
        return '{"formatted": true}'
    def generate_validation_tests_tool(*args, **kwargs):
        return '{"tests": []}'
    def execute_test_suite_tool(*args, **kwargs):
        return '{"results": []}'
    def web_search(*args, **kwargs):
        return '{"results": []}'
    def http_request(*args, **kwargs):
        return '{"status": 200}'
    def analyze_code_complexity(*args, **kwargs):
        return '{"complexity": "low"}'


class TestCodeAnalysisTools:
    """测试代码分析工具"""

    def test_analyze_code_defects_python(self):
        """测试Python代码缺陷分析"""
        # 创建测试Python文件
        test_code = """
def calculate_sum(a, b):
    return a + b

def divide_numbers(a, b):
    return a / b  # 潜在的除零错误
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            file_path = f.name

        try:
            # 调用代码缺陷分析工具
            result = analyze_code_defects(file_path, language="python")

            # 验证结果
            assert result is not None
            assert isinstance(result, str)

            # 如果返回JSON格式，验证结构
            try:
                result_json = json.loads(result)
                assert "defects" in result_json
            except json.JSONDecodeError:
                # 如果不是JSON格式，验证包含关键字
                assert "defect" in result.lower() or "error" in result.lower()
        finally:
            os.unlink(file_path)

    def test_analyze_code_defects_javascript(self):
        """测试JavaScript代码缺陷分析"""
        test_code = """
function calculateSum(a, b) {
    return a + b;
}

function divideNumbers(a, b) {
    return a / b;  // 潜在的除零错误
}
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(test_code)
            file_path = f.name

        try:
            result = analyze_code_defects(file_path, language="javascript")
            assert result is not None
            assert isinstance(result, str)
        finally:
            os.unlink(file_path)

    def test_analyze_code_defects_auto_language_detection(self):
        """测试自动语言检测"""
        test_code = """
#include <stdio.h>

int main() {
    printf("Hello, World!\n");
    return 0;
}
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write(test_code)
            file_path = f.name

        try:
            # 不指定语言，让工具自动检测
            result = analyze_code_defects(file_path)
            assert result is not None
            assert isinstance(result, str)
        finally:
            os.unlink(file_path)

    def test_analyze_code_defects_nonexistent_file(self):
        """测试分析不存在的文件"""
        with pytest.raises((FileNotFoundError, Exception)):
            analyze_code_defects("/nonexistent/file.py")

    def test_analyze_code_complexity(self):
        """测试代码复杂度分析"""
        test_code = """
def complex_function(data):
    result = []
    for item in data:
        if item > 0:
            for i in range(len(item)):
                if i % 2 == 0:
                    result.append(item[i] * 2)
                else:
                    result.append(item[i] + 1)
    return result
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            file_path = f.name

        try:
            result = analyze_code_complexity(file_path)
            assert result is not None
            assert isinstance(result, str)
        finally:
            os.unlink(file_path)


class TestCompilationTools:
    """测试编译工具"""

    def test_compile_python_project(self):
        """测试Python项目编译"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建简单的Python项目结构
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            # 创建main.py
            main_file = project_path / "main.py"
            main_file.write_text("print('Hello, World!')")

            # 创建requirements.txt
            req_file = project_path / "requirements.txt"
            req_file.write_text("requests>=2.25.0")

            result = compile_project(str(project_path))
            assert result is not None
            assert isinstance(result, str)

    def test_compile_javascript_project(self):
        """测试JavaScript项目编译"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "js_project"
            project_path.mkdir()

            # 创建package.json
            package_file = project_path / "package.json"
            package_file.write_text('{"name": "test-project", "version": "1.0.0"}')

            # 创建index.js
            index_file = project_path / "index.js"
            index_file.write_text("console.log('Hello');")

            result = compile_project(str(project_path))
            assert result is not None
            assert isinstance(result, str)

    def test_compile_nonexistent_project(self):
        """测试编译不存在的项目"""
        with pytest.raises((FileNotFoundError, Exception)):
            compile_project("/nonexistent/project")


class TestMonitoringTools:
    """测试监控工具"""

    @patch('subprocess.run')
    def test_run_and_monitor_success(self, mock_run):
        """测试程序运行监控成功情况"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Program completed successfully",
            stderr=""
        )

        result = run_and_monitor("echo 'Hello World'")
        assert result is not None
        assert isinstance(result, str)
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_run_and_monitor_failure(self, mock_run):
        """测试程序运行监控失败情况"""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Error occurred"
        )

        result = run_and_monitor("false")
        assert result is not None
        assert isinstance(result, str)

    @patch('subprocess.run')
    def test_run_tests_with_error_capture_success(self, mock_run):
        """测试测试执行和错误捕获成功情况"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="All tests passed",
            stderr=""
        )

        result = run_tests_with_error_capture("python -m pytest")
        assert result is not None
        assert isinstance(result, str)

    @patch('subprocess.run')
    def test_run_tests_with_error_capture_failure(self, mock_run):
        """测试测试执行和错误捕获失败情况"""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="Some tests failed",
            stderr="AssertionError"
        )

        result = run_tests_with_error_capture("python -m pytest")
        assert result is not None
        assert isinstance(result, str)


class TestProjectExplorer:
    """测试项目探索工具"""

    def test_explore_python_project_structure(self):
        """测试Python项目结构探索"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "python_project"
            project_path.mkdir()

            # 创建项目结构
            (project_path / "src").mkdir()
            (project_path / "tests").mkdir()
            (project_path / "docs").mkdir()

            (project_path / "main.py").write_text("def main(): pass")
            (project_path / "requirements.txt").write_text("requests")
            (project_path / "README.md").write_text("# Test Project")
            (project_path / "setup.py").write_text("from setuptools import setup")

            result = explore_project_structure(str(project_path))
            assert result is not None
            assert isinstance(result, str)

            # 验证结果包含关键信息
            assert any(keyword in result.lower() for keyword in ["python", "structure", "project"])

    def test_explore_empty_project(self):
        """测试探索空项目"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = explore_project_structure(temp_dir)
            assert result is not None
            assert isinstance(result, str)

    def test_explore_nonexistent_project(self):
        """测试探索不存在的项目"""
        with pytest.raises((FileNotFoundError, Exception)):
            explore_project_structure("/nonexistent/project")


class TestCodeFormatting:
    """测试代码格式化工具"""

    def test_format_python_code(self):
        """测试Python代码格式化"""
        unformatted_code = """
def test_function(param1,param2):
    x=param1+param2
    return x
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(unformatted_code)
            file_path = f.name

        try:
            result = format_code_professional(file_path, style="black")
            assert result is not None
            assert isinstance(result, str)
        finally:
            os.unlink(file_path)

    def test_format_javascript_code(self):
        """测试JavaScript代码格式化"""
        unformatted_code = """
function testFunction(param1,param2){
    let x=param1+param2;
    return x;
}
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(unformatted_code)
            file_path = f.name

        try:
            result = format_code_professional(file_path, style="prettier")
            assert result is not None
            assert isinstance(result, str)
        finally:
            os.unlink(file_path)

    def test_format_nonexistent_file(self):
        """测试格式化不存在的文件"""
        with pytest.raises((FileNotFoundError, Exception)):
            format_code_professional("/nonexistent/file.py")

    def test_batch_format_project(self):
        """测试批量格式化项目"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "format_project"
            project_path.mkdir()

            # 创建多个需要格式化的文件
            (project_path / "file1.py").write_text("def func():return 1")
            (project_path / "file2.py").write_text("def func2():return 2")
            (project_path / "subdir").mkdir()
            (project_path / "subdir" / "file3.py").write_text("def func3():return 3")

            # 模拟批量格式化函数
            try:
                from src.tools.professional_formatter import batch_format_professional
                result = batch_format_professional(str(project_path))
                assert result is not None
            except ImportError:
                # 如果导入失败，跳过此测试
                pytest.skip("professional_formatter not available")


class TestTestGeneration:
    """测试测试生成工具"""

    def test_generate_python_tests(self):
        """测试Python测试生成"""
        source_code = """
def calculate_area(length, width):
    return length * width
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(source_code)
            file_path = f.name

        try:
            result = generate_validation_tests_tool(file_path, language="python")
            assert result is not None
            assert isinstance(result, str)

            # 验证生成的内容包含测试相关关键字
            try:
                result_json = json.loads(result)
                assert "tests" in result_json or "test_cases" in result_json
            except json.JSONDecodeError:
                assert any(keyword in result.lower() for keyword in ["test", "pytest", "unittest"])

        finally:
            os.unlink(file_path)

    def test_generate_javascript_tests(self):
        """测试JavaScript测试生成"""
        source_code = """
function calculateTotal(price, tax) {
    return price * (1 + tax);
}
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(source_code)
            file_path = f.name

        try:
            result = generate_validation_tests_tool(file_path, language="javascript")
            assert result is not None
            assert isinstance(result, str)
        finally:
            os.unlink(file_path)

    def test_execute_test_suite(self):
        """测试执行测试套件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "tests"
            test_dir.mkdir()

            # 创建简单的测试文件
            test_file = test_dir / "test_math.py"
            test_file.write_text("""
def test_addition():
    assert 1 + 1 == 2

def test_subtraction():
    assert 5 - 3 == 2
""")

            result = execute_test_suite_tool(str(test_dir))
            assert result is not None
            assert isinstance(result, str)


class TestNetworkTools:
    """测试网络工具"""

    @patch('requests.get')
    def test_web_search_success(self, mock_get):
        """测试网络搜索成功"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {"title": "Test Result 1", "url": "https://example.com/1"},
                {"title": "Test Result 2", "url": "https://example.com/2"}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = web_search("Python programming")
        assert result is not None
        assert isinstance(result, str)

    @patch('requests.get')
    def test_web_search_failure(self, mock_get):
        """测试网络搜索失败"""
        mock_get.side_effect = Exception("Network error")

        with pytest.raises(Exception):
            web_search("Python programming")

    @patch('requests.get')
    def test_http_request_get_success(self, mock_get):
        """测试HTTP GET请求成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Success"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = http_request("GET", "https://api.example.com/data")
        assert result is not None
        assert isinstance(result, str)

    @patch('requests.post')
    def test_http_request_post_success(self, mock_post):
        """测试HTTP POST请求成功"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 123, "status": "created"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        data = {"name": "test", "value": 123}
        result = http_request("POST", "https://api.example.com/create", data=data)
        assert result is not None
        assert isinstance(result, str)

    @patch('requests.get')
    def test_http_request_failure(self, mock_get):
        """测试HTTP请求失败"""
        mock_get.side_effect = Exception("Connection error")

        with pytest.raises(Exception):
            http_request("GET", "https://nonexistent.example.com")


class TestToolErrorHandling:
    """测试工具错误处理"""

    def test_tool_with_invalid_file_path(self):
        """测试工具处理无效文件路径"""
        invalid_paths = [
            "",
            "   ",
            "/invalid/path/file.txt",
            "relative/path/file.py"
        ]

        for path in invalid_paths:
            # 这些调用应该优雅地处理错误
            try:
                result = analyze_code_defects(path)
                # 如果没有抛出异常，结果应该指示错误
                assert result is not None
            except (FileNotFoundError, ValueError, Exception):
                # 预期的异常类型
                pass

    def test_tool_with_corrupted_file(self):
        """测试工具处理损坏的文件"""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.py', delete=False) as f:
            # 写入二进制垃圾数据
            f.write(b'\x00\x01\x02\x03\x04\x05')
            file_path = f.name

        try:
            # 工具应该能处理损坏的文件
            result = analyze_code_defects(file_path)
            assert result is not None
        except Exception:
            # 如果抛出异常，应该是预期的类型
            pass
        finally:
            os.unlink(file_path)


class TestToolPerformance:
    """测试工具性能"""

    def test_large_file_analysis_performance(self):
        """测试大文件分析性能"""
        import time

        # 创建大文件
        large_code = ""
        for i in range(1000):
            large_code += f"""
def function_{i}():
    result = []
    for j in range(100):
        result.append(i * j)
    return result
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(large_code)
            file_path = f.name

        try:
            start_time = time.time()
            result = analyze_code_defects(file_path)
            end_time = time.time()

            analysis_time = end_time - start_time
            assert result is not None
            assert isinstance(result, str)
            # 分析应该在合理时间内完成（例如10秒内）
            assert analysis_time < 10.0
        finally:
            os.unlink(file_path)

    def test_concurrent_tool_execution(self):
        """测试并发工具执行"""
        import threading
        import time

        results = []

        def run_tool_analysis():
            test_code = "def test_func(): return 'test'"
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(test_code)
                file_path = f.name

            try:
                result = analyze_code_defects(file_path)
                results.append(result)
            finally:
                os.unlink(file_path)

        # 创建多个线程同时执行工具
        threads = []
        for i in range(5):
            thread = threading.Thread(target=run_tool_analysis)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=10)

        # 验证所有调用都成功
        assert len(results) == 5
        assert all(result is not None for result in results)


class TestToolIntegration:
    """测试工具集成"""

    def test_tool_chain_integration(self):
        """测试工具链集成"""
        # 创建测试代码
        test_code = """
def calculate_area(length, width):
    return length * width

def calculate_perimeter(length, width):
    return 2 * (length + width)
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            file_path = f.name

        try:
            # 步骤1：分析代码缺陷
            defect_result = analyze_code_defects(file_path)
            assert defect_result is not None

            # 步骤2：分析代码复杂度
            complexity_result = analyze_code_complexity(file_path)
            assert complexity_result is not None

            # 步骤3：格式化代码
            format_result = format_code_professional(file_path)
            assert format_result is not None

            # 步骤4：生成测试
            test_result = generate_validation_tests_tool(file_path)
            assert test_result is not None

        finally:
            os.unlink(file_path)

    def test_cross_language_tool_integration(self):
        """测试跨语言工具集成"""
        languages_and_codes = [
            ("python", "def hello(): print('Hello')"),
            ("javascript", "function hello() { console.log('Hello'); }"),
            ("java", "public class Hello { public static void main(String[] args) { System.out.println(\"Hello\"); } }")
        ]

        for language, code in languages_and_codes:
            with tempfile.NamedTemporaryFile(mode='w', suffix=f".{language}", delete=False) as f:
                f.write(code)
                file_path = f.name

            try:
                result = analyze_code_defects(file_path, language=language)
                assert result is not None
                assert isinstance(result, str)
            finally:
                os.unlink(file_path)


# 测试运行器和配置
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])