"""
pytest配置文件

提供测试夹具和全局配置
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture
def temp_dir():
    """创建临时目录夹具"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def temp_file(temp_dir):
    """创建临时文件夹具"""

    def create_temp_file(suffix=".txt", content=""):
        file_path = temp_dir / f"test_{temp_file.counter}{suffix}"
        temp_file.counter += 1
        file_path.write_text(content)
        return file_path

    temp_file.counter = 1
    return create_temp_file


@pytest.fixture
def sample_python_file(temp_dir):
    """创建Python示例文件夹具"""
    python_code = '''
def calculate_factorial(n):
    """计算阶乘的函数"""
    if n <= 1:
        return 1
    return n * calculate_factorial(n - 1)

def fibonacci(n):
    """生成斐波那契数列"""
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]

    sequence = [0, 1]
    for i in range(2, n):
        sequence.append(sequence[-1] + sequence[-2])
    return sequence

class Calculator:
    """简单计算器类"""

    def __init__(self):
        self.history = []

    def add(self, a, b):
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result

    def multiply(self, a, b):
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result

    def get_history(self):
        return self.history.copy()

if __name__ == "__main__":
    # 测试代码
    calc = Calculator()
    print(calc.add(5, 3))
    print(calc.multiply(4, 6))
    print(calc.get_history())

    print("Factorial of 5:", calculate_factorial(5))
    print("Fibonacci sequence (first 10):", fibonacci(10))
'''

    python_file = temp_dir / "sample_code.py"
    python_file.write_text(python_code)
    return python_file


@pytest.fixture
def sample_javascript_file(temp_dir):
    """创建JavaScript示例文件夹具"""
    js_code = """
// JavaScript示例代码
class User {
    constructor(name, email) {
        this.name = name;
        this.email = email;
        this.createdAt = new Date();
    }

    // 用户验证
    validate() {
        const errors = [];

        if (!this.name || this.name.trim().length < 2) {
            errors.push("Name must be at least 2 characters");
        }

        if (!this.email || !this.isValidEmail(this.email)) {
            errors.push("Valid email is required");
        }

        return {
            isValid: errors.length === 0,
            errors: errors
        };
    }

    // 邮箱验证
    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    // 用户信息
    getUserInfo() {
        return {
            name: this.name,
            email: this.email,
            created: this.createdAt.toISOString(),
            daysSinceCreated: Math.floor((Date.now() - this.createdAt) / (1000 * 60 * 60 * 24))
        };
    }
}

// 工具函数
function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 测试代码
const user = new User("John Doe", "john@example.com");
console.log(user.validate());
console.log(user.getUserInfo());

console.log(formatCurrency(1234.56));
"""

    js_file = temp_dir / "sample_code.js"
    js_file.write_text(js_code)
    return js_file


@pytest.fixture
def sample_project_structure(temp_dir):
    """创建示例项目结构夹具"""
    project_dir = temp_dir / "sample_project"
    project_dir.mkdir()

    # 创建目录结构
    (project_dir / "src").mkdir()
    (project_dir / "tests").mkdir()
    (project_dir / "docs").mkdir()
    (project_dir / "config").mkdir()

    # 创建Python文件
    (project_dir / "main.py").write_text(
        '''
#!/usr/bin/env python3
"""主程序入口"""
from src.app import create_app

def main():
    app = create_app()
    app.run()

if __name__ == "__main__":
    main()
'''
    )

    (project_dir / "src" / "__init__.py").write_text("")
    (project_dir / "src" / "app.py").write_text(
        '''
"""应用程序配置"""
from flask import Flask

def create_app():
    app = Flask(__name__)

    @app.route('/')
    def hello():
        return "Hello, World!"

    return app
'''
    )

    (project_dir / "tests" / "test_app.py").write_text(
        '''
"""应用程序测试"""
import pytest
from src.app import create_app

def test_hello_world():
    app = create_app()
    client = app.test_client()

    response = client.get('/')
    assert response.status_code == 200
    assert b"Hello, World!" in response.data
'''
    )

    # 创建配置文件
    (project_dir / "requirements.txt").write_text(
        """
Flask>=2.0.0
pytest>=6.0.0
gunicorn>=20.0.0
"""
    )

    (project_dir / "README.md").write_text(
        """
# Sample Project

这是一个示例项目，用于演示项目结构分析功能。

## 功能

- Web应用程序
- 自动化测试
- 完整的文档

## 安装和运行

```bash
pip install -r requirements.txt
python main.py
```
"""
    )

    (project_dir / ".gitignore").write_text(
        """
__pycache__/
*.pyc
.env
venv/
node_modules/
"""
    )

    return project_dir


@pytest.fixture
def mock_memory_files(temp_dir):
    """创建模拟记忆文件夹具"""
    memory_dir = temp_dir / "memories"
    memory_dir.mkdir()

    # 创建记忆文件
    (memory_dir / "python_basics.md").write_text(
        """
# Python基础知识

## 基本语法
- 缩进是Python的重要特征
- 变量命名遵循蛇形命名法
- 使用注释提高代码可读性

## 数据类型
- int, float, str, bool
- list, tuple, dict, set
- None类型

## 控制流
- if/elif/else条件语句
- for/while循环
- break/continue语句

## 函数
- def关键字定义函数
- 参数传递和返回值
- 默认参数和关键字参数
"""
    )

    (memory_dir / "javascript_tips.md").write_text(
        """
# JavaScript编程技巧

## 最佳实践
- 使用const和let而不是var
- 避免全局变量污染
- 使用箭头函数简化代码

## ES6+特性
- 解构赋值
- 模板字符串
- 扩展运算符
- Promise和async/await

## 调试技巧
- 使用console.log调试
- 利用浏览器开发者工具
- 使用断点调试
"""
    )

    (memory_dir / "project_patterns.md").write_text(
        """
# 项目设计模式

## 创建型模式
- 工厂模式
- 建造者模式
- 单例模式

## 结构型模式
- 适配器模式
- 装饰器模式
- 代理模式

## 行为型模式
- 观察者模式
- 策略模式
- 命令模式

## 适用场景
- 根据项目需求选择合适的模式
- 避免过度设计
- 保持代码简洁性
"""
    )

    return memory_dir


@pytest.fixture
def mock_agent_responses():
    """模拟Agent响应夹具"""
    return [
        {"content": "我来分析您的代码。", "type": "text"},
        {"content": "代码分析完成，发现以下问题：", "type": "text"},
        {
            "tool_call": {
                "name": "analyze_code_defects",
                "args": {"file_path": "test.py"},
            },
            "type": "tool_call",
        },
        {"content": "建议进行以下改进：", "type": "text"},
    ]


@pytest.fixture
def error_prone_code(temp_dir):
    """创建有错误的代码示例夹具"""
    error_code = """
def divide_numbers(a, b):
    return a / b  # 潜在除零错误

def process_list(items):
    result = []
    for item in items:
        # 缺少边界检查
        result.append(items[item])  # 可能的索引错误
    return result

def calculate_discount(price, discount_rate):
    # 没有验证输入参数
    return price * (discount_rate / 100)

def read_file(filename):
    f = open(filename, 'r')  # 没有使用with语句，文件可能不会关闭
    content = f.read()
    return content

# 逻辑错误
def is_adult(age):
    if age >= 18:
        return True
    elif age < 0:
        return False
    # 缺少age介于0-18之间的处理

# 性能问题
def find_duplicate_slow(arr):
    duplicates = []
    for i in range(len(arr)):
        for j in range(i+1, len(arr)):
            if arr[i] == arr[j] and arr[i] not in duplicates:
                duplicates.append(arr[i])
    return duplicates
"""

    error_file = temp_dir / "error_prone_code.py"
    error_file.write_text(error_code)
    return error_file


# 测试标记
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line(
        "markers", "requires_network: marks tests that require network access"
    )


# 测试收集配置
def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    # 为没有标记的测试添加默认标记
    for item in items:
        if not any(item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# 测试钩子
@pytest.fixture(autouse=True)
def setup_test_environment():
    """设置测试环境"""
    # 设置测试环境变量
    os.environ["TESTING"] = "true"
    os.environ["FIX_AGENT_TEST_MODE"] = "true"

    yield

    # 清理测试环境
    os.environ.pop("TESTING", None)
    os.environ.pop("FIX_AGENT_TEST_MODE", None)
