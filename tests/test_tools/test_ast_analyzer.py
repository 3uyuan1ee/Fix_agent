"""
AST静态分析工具单元测试
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.tools.ast_analyzer import ASTAnalyzer, ASTAnalysisError


class TestASTAnalyzer:
    """AST分析器测试类"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.analyzer = ASTAnalyzer()

    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_valid_python_file(self):
        """测试解析有效的Python文件"""
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

        # 解析文件
        result = self.analyzer.analyze_file(str(test_file))

        # 验证结果
        assert result is not None
        assert "errors" in result
        assert len(result["errors"]) == 0
        assert "functions" in result
        assert "classes" in result
        assert "imports" in result

    def test_parse_syntax_error_file(self):
        """测试解析语法错误的文件"""
        # 创建有语法错误的Python文件
        test_code = '''
def broken_function()
    print("缺少冒号")
'''
        test_file = Path(self.temp_dir) / "broken.py"
        test_file.write_text(test_code)

        # 解析文件
        result = self.analyzer.analyze_file(str(test_file))

        # 验证结果
        assert result is not None
        assert "errors" in result
        assert len(result["errors"]) > 0
        assert any("Syntax error" in error["message"] for error in result["errors"])

    def test_extract_functions(self):
        """测试提取函数定义"""
        test_code = '''
def function1():
    """函数1"""
    pass

def function2(arg1, arg2="default"):
    """函数2"""
    return arg1 + arg2

async def async_function():
    """异步函数"""
    pass
'''
        test_file = Path(self.temp_dir) / "functions.py"
        test_file.write_text(test_code)

        result = self.analyzer.analyze_file(str(test_file))

        # 验证函数提取
        functions = result["functions"]
        assert len(functions) == 3

        function_names = [f["name"] for f in functions]
        assert "function1" in function_names
        assert "function2" in function_names
        assert "async_function" in function_names

        # 验证函数2的参数
        func2 = next(f for f in functions if f["name"] == "function2")
        assert len(func2["args"]) == 2
        assert "arg1" in func2["args"]
        assert "arg2" in func2["args"]

    def test_extract_classes(self):
        """测试提取类定义"""
        test_code = '''
class MyClass:
    """我的类"""

    def __init__(self):
        self.attr = "value"

    def method1(self):
        pass

class ChildClass(MyClass):
    """子类"""

    def child_method(self):
        pass
'''
        test_file = Path(self.temp_dir) / "classes.py"
        test_file.write_text(test_code)

        result = self.analyzer.analyze_file(str(test_file))

        # 验证类提取
        classes = result["classes"]
        assert len(classes) == 2

        class_names = [c["name"] for c in classes]
        assert "MyClass" in class_names
        assert "ChildClass" in class_names

        # 验证继承关系
        child_class = next(c for c in classes if c["name"] == "ChildClass")
        assert "MyClass" in child_class["bases"]

    def test_extract_variables(self):
        """测试提取变量定义"""
        test_code = '''
# 模块级别变量
MODULE_VAR = "module_value"
CONSTANT = 42

def function():
    # 函数局部变量
    local_var = "local"
    return local_var

class TestClass:
    # 类变量
    class_var = "class_value"

    def __init__(self):
        # 实例变量
        self.instance_var = "instance_value"
'''
        test_file = Path(self.temp_dir) / "variables.py"
        test_file.write_text(test_code)

        result = self.analyzer.analyze_file(str(test_file))

        # 验证变量提取
        variables = result["variables"]
        assert len(variables) >= 2  # 至少有模块级别变量

        var_names = [v["name"] for v in variables]
        assert "MODULE_VAR" in var_names
        assert "CONSTANT" in var_names

    def test_extract_imports(self):
        """测试提取导入依赖"""
        test_code = '''
import os
import sys as system
from pathlib import Path
from collections import defaultdict
from my_package.submodule import specific_function
import numpy as np
'''
        test_file = Path(self.temp_dir) / "imports.py"
        test_file.write_text(test_code)

        result = self.analyzer.analyze_file(str(test_file))

        # 验证导入提取
        imports = result["imports"]
        assert len(imports) >= 6

        import_modules = [imp["module"] for imp in imports]
        assert "os" in import_modules
        assert "pathlib" in import_modules
        assert "collections" in import_modules
        assert "my_package.submodule" in import_modules
        assert "numpy" in import_modules

    def test_analyze_complexity(self):
        """测试代码复杂度分析"""
        test_code = '''
def simple_function():
    return 1

def complex_function(x):
    if x > 0:
        if x > 10:
            for i in range(x):
                if i % 2 == 0:
                    try:
                        result = i / 0
                    except ZeroDivisionError:
                        result = 0
                else:
                    result = i
        else:
            result = x
    else:
        result = 0
    return result
'''
        test_file = Path(self.temp_dir) / "complexity.py"
        test_file.write_text(test_code)

        result = self.analyzer.analyze_file(str(test_file))

        # 验证复杂度分析
        functions = result["functions"]
        simple_func = next(f for f in functions if f["name"] == "simple_function")
        complex_func = next(f for f in functions if f["name"] == "complex_function")

        assert simple_func["complexity"] == 1
        assert complex_func["complexity"] > 1

    def test_nonexistent_file(self):
        """测试分析不存在的文件"""
        with pytest.raises(ASTAnalysisError) as exc_info:
            self.analyzer.analyze_file("/nonexistent/file.py")

        assert "does not exist" in str(exc_info.value)

    def test_non_python_file(self):
        """测试分析非Python文件"""
        # 创建非Python文件
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("This is not Python code")

        with pytest.raises(ASTAnalysisError) as exc_info:
            self.analyzer.analyze_file(str(test_file))

        assert "not a Python file" in str(exc_info.value)

    def test_empty_file(self):
        """测试分析空文件"""
        test_file = Path(self.temp_dir) / "empty.py"
        test_file.write_text("")

        result = self.analyzer.analyze_file(str(test_file))

        # 空文件应该没有错误，但也没有内容
        assert result is not None
        assert len(result["errors"]) == 0
        assert len(result["functions"]) == 0
        assert len(result["classes"]) == 0

    def test_file_with_encoding_issues(self):
        """测试文件编码问题处理"""
        # 创建包含特殊字符的文件
        test_code = '''
# 中文注释
def test_function():
    """中文文档字符串"""
    print("测试内容")
'''
        test_file = Path(self.temp_dir) / "encoding.py"
        test_file.write_text(test_code, encoding="utf-8")

        result = self.analyzer.analyze_file(str(test_file))

        # 应该能够正常处理
        assert result is not None
        assert len(result["errors"]) == 0
        assert len(result["functions"]) == 1

    def test_get_analysis_summary(self):
        """测试获取分析摘要"""
        test_code = '''
import os

def function1():
    pass

def function2(x):
    if x > 0:
        return x
    return 0

class TestClass:
    def method(self):
        pass
'''
        test_file = Path(self.temp_dir) / "summary.py"
        test_file.write_text(test_code)

        result = self.analyzer.analyze_file(str(test_file))
        summary = self.analyzer.get_analysis_summary(result)

        # 验证摘要信息
        assert "file_path" in summary
        assert "total_functions" in summary
        assert "total_classes" in summary
        assert "total_imports" in summary
        assert "max_complexity" in summary
        assert "error_count" in summary

        assert summary["total_functions"] == 2
        assert summary["total_classes"] == 1
        assert summary["total_imports"] == 1
        assert summary["error_count"] == 0