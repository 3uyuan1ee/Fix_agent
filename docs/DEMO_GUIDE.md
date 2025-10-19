# 🎭 AIDefectDetector 演示指南

本指南将带你逐步体验AIDefectDetector的各种功能，通过实际的演示代码了解系统的强大能力。

## 📋 演示文件列表

| 演示文件 | 功能描述 | 对应任务 |
|---------|---------|---------|
| `demo_t018_static_analysis.py` | 静态分析功能演示 | T018 |
| `demo_t019_deep_analysis.py` | 深度分析功能演示 | T019 |
| `demo_t021_orchestrator.py` | 任务编排器演示 | T021 |
| `demo_t022_mode_routing.py` | 模式路由演示 | T022 |
| `demo_t023_user_interaction.py` | 用户交互演示 | T023 |
| `demo_t024_cli_interface.py` | CLI界面演示 | T024 |
| `demo_t025_static_analysis_command.py` | 静态分析命令演示 | T025 |
| `demo_t026_deep_analysis_interaction.py` | 深度分析交互演示 | T026 |
| `demo_t027_fix_analysis_interaction.py` | 修复分析交互演示 | T027 |

## 🚀 快速开始

### 前置准备

```bash
# 确保环境已激活
source .venv/bin/activate

# 进入项目目录
cd AIDefectDetector

# 确保依赖已安装
pip install -r requirements.txt
```

## 📊 演示1：静态分析功能 (T018)

### 运行演示

```bash
python demo_t018_static_analysis.py
```

### 演示内容

这个演示展示了系统的静态分析能力：

```python
# 创建示例代码
sample_code = '''
import os
import sys

def calculate_sum(numbers):
    result = 0
    for num in numbers:
        result += num
    return result

def unused_function():
    print("This function is never called")

if __name__ == "__main__":
    numbers = [1, 2, 3, 4, 5]
    print(calculate_sum(numbers))
'''
```

**预期输出**：
- AST语法分析结果
- Pylint代码质量检查
- Flake8代码风格检查
- Bandit安全漏洞检测

### 学习要点

1. **多工具集成**：了解如何集成多种分析工具
2. **结果聚合**：学习如何整合不同工具的分析结果
3. **报告生成**：掌握生成统一分析报告的方法

## 🧠 演示2：深度分析功能 (T019)

### 运行演示

```bash
# 需要先配置API密钥
export OPENAI_API_KEY="your-openai-key"
# 或
export ANTHROPIC_API_KEY="your-anthropic-key"

python demo_t019_deep_analysis.py
```

### 演示内容

这个演示展示了AI驱动的深度分析能力：

```python
# 复杂代码示例
complex_code = '''
class DataProcessor:
    def __init__(self, config):
        self.config = config
        self.data_cache = {}

    def process_data(self, raw_data):
        # 复杂的数据处理逻辑
        processed_data = []
        for item in raw_data:
            if self._validate_item(item):
                processed_item = self._transform_item(item)
                processed_data.append(processed_item)
        return processed_data

    def _validate_item(self, item):
        # 验证逻辑
        return item is not None and hasattr(item, 'id')

    def _transform_item(self, item):
        # 转换逻辑
        return {
            'id': item.id,
            'processed_at': datetime.now().isoformat(),
            'data': item.data
        }
'''
```

**预期输出**：
- AI代码分析报告
- 改进建议
- 潜在问题识别
- 最佳实践建议

### 学习要点

1. **AI集成**：了解如何集成大语言模型
2. **提示词工程**：学习有效的提示词设计
3. **结果解析**：掌握AI分析结果的解析方法

## 🎭 演示3：任务编排器 (T021)

### 运行演示

```bash
python demo_t021_orchestrator.py
```

### 演示内容

这个演示展示了AI Agent的任务编排能力：

```python
# 模拟用户请求
user_requests = [
    "请分析我的Python项目代码质量",
    "帮我检查这个文件的安全问题",
    "我想重构这段代码，需要建议"
]
```

**预期输出**：
- 任务规划结果
- 执行步骤分解
- 会话状态管理
- 上下文记忆

### 学习要点

1. **Agent架构**：理解AI Agent的核心架构
2. **任务规划**：学习如何将复杂请求分解为任务
3. **状态管理**：掌握会话状态的管理方法

## 🔄 演示4：模式路由 (T022)

### 运行演示

```bash
python demo_t022_mode_routing.py
```

### 演示内容

这个演示展示了智能模式路由功能：

```python
# 测试不同类型的用户输入
test_inputs = [
    "静态分析我的代码",      # 应路由到静态分析
    "深度分析项目架构",      # 应路由到深度分析
    "修复这个安全漏洞",      # 应路由到修复分析
    "继续分析",              # 基于上下文路由
    "/static check src/"    # 命令模式路由
]
```

**预期输出**：
- 模式识别结果
- 置信度评分
- 路由决策
- 上下文理解

### 学习要点

1. **意图识别**：理解如何识别用户意图
2. **模式匹配**：学习关键词和模式匹配算法
3. **上下文理解**：掌握基于上下文的决策方法

## 💬 演示5：用户交互 (T023)

### 运行演示

```bash
python demo_t023_user_interaction.py
```

### 演示内容

这个演示展示了用户交互功能：

```python
# 交互式对话示例
interactive_session = [
    "我想分析这个Python项目",
    "请帮我检查代码质量",
    "有什么改进建议吗？",
    "可以详细解释一下这个问题吗？"
]
```

**预期输出**：
- 交互式对话
- 自然语言理解
- 上下文相关的响应
- 多轮对话管理

### 学习要点

1. **对话管理**：理解多轮对话的管理方法
2. **自然语言处理**：学习处理用户输入的技巧
3. **响应生成**：掌握生成相关响应的方法

## 💻 演示6：CLI界面 (T024)

### 运行演示

```bash
python demo_t024_cli_interface.py
```

### 演示内容

这个演示展示了命令行界面的使用：

```python
# 模拟CLI命令
cli_commands = [
    ["analyze", "static", "./src"],
    ["analyze", "deep", "./src", "--model", "gpt-4"],
    ["analyze", "fix", "./src", "--output", "results.json"],
    ["status", "--task-id", "task_123"],
    ["help"]
]
```

**预期输出**：
- 命令解析结果
- 参数验证
- 命令执行
- 结果格式化输出

### 学习要点

1. **命令行设计**：理解CLI界面的设计原则
2. **参数解析**：学习命令行参数的解析方法
3. **输出格式化**：掌握结果输出的格式化技巧

## 🔧 演示7：静态分析命令 (T025)

### 运行演示

```bash
python demo_t025_static_analysis_command.py
```

### 演示内容

这个演示专门展示了静态分析命令的详细功能：

```python
# 静态分析选项
analysis_options = {
    'target_path': './src',
    'tools': ['pylint', 'flake8', 'bandit', 'ast'],
    'parallel': True,
    'output_format': 'json',
    'include_tests': False,
    'max_files': 100
}
```

**预期输出**：
- 详细的静态分析结果
- 工具配置选项
- 并行处理效果
- 多种输出格式

### 学习要点

1. **工具配置**：理解分析工具的配置方法
2. **并行处理**：学习并行分析的技术
3. **结果聚合**：掌握多工具结果的整合方法

## 🎯 演示8：深度分析交互 (T026)

### 运行演示

```bash
# 确保已配置API密钥
python demo_t026_deep_analysis_interaction.py
```

### 演示内容

这个演示展示了深度分析的交互过程：

```python
# 深度分析交互流程
interaction_flow = [
    "开始深度分析",
    "选择分析重点",
    "获取AI建议",
    "深入探讨问题",
    "总结分析结果"
]
```

**预期输出**：
- 交互式深度分析
- AI建议展示
- 问题深入探讨
- 分析结果总结

### 学习要点

1. **交互流程**：理解深度分析的交互设计
2. **AI对话**：学习与AI的对话技巧
3. **结果展示**：掌握分析结果的有效展示

## 🛠️ 演示9：修复分析交互 (T027)

### 运行演示

```bash
python demo_t027_fix_analysis_interaction.py
```

### 演示内容

这个演示展示了修复分析的完整流程：

```python
# 修复分析流程
fix_workflow = [
    "检测代码问题",
    "生成修复建议",
    "展示修复前后对比",
    "确认修复操作",
    "执行修复并验证"
]
```

**预期输出**：
- 问题检测结果
- 修复建议生成
- 代码对比展示
- 修复执行过程

### 学习要点

1. **问题检测**：理解代码问题的检测方法
2. **修复建议**：学习生成修复建议的技巧
3. **安全修复**：掌握安全修复操作的方法

## 🎯 演示学习路径

### 初学者路径

1. **demo_t018_static_analysis.py** → 了解基础分析功能
2. **demo_t024_cli_interface.py** → 学习命令行使用
3. **demo_t025_static_analysis_command.py** → 掌握静态分析

### 进阶路径

1. **demo_t019_deep_analysis.py** → 体验AI分析能力
2. **demo_t021_orchestrator.py** → 理解Agent架构
3. **demo_t022_mode_routing.py** → 学习智能路由

### 高级路径

1. **demo_t023_user_interaction.py** → 掌握交互设计
2. **demo_t026_deep_analysis_interaction.py** → 深入AI交互
3. **demo_t027_fix_analysis_interaction.py** → 完整修复流程

## 💡 演示使用技巧

### 1. 逐步运行

建议按照任务编号顺序运行演示，体验功能演进过程：

```bash
# 按顺序运行
python demo_t018_static_analysis.py
python demo_t019_deep_analysis.py
python demo_t021_orchestrator.py
# ... 以此类推
```

### 2. 修改参数

每个演示文件都可以修改参数来体验不同功能：

```python
# 修改分析目标
target_path = "./your_project"

# 修改分析工具
tools = ["pylint", "flake8"]

# 修改输出格式
output_format = "html"
```

### 3. 集成测试

可以将多个演示组合起来进行集成测试：

```python
# 先运行静态分析，再运行深度分析
static_results = run_static_analysis("./src")
deep_results = run_deep_analysis("./src", context=static_results)
```

### 4. 性能监控

在运行演示时，可以监控系统性能：

```python
import time
import psutil

start_time = time.time()
start_memory = psutil.Process().memory_info().rss

# 运行演示
run_demo()

end_time = time.time()
end_memory = psutil.Process().memory_info().rss

print(f"运行时间: {end_time - start_time:.2f}秒")
print(f"内存使用: {(end_memory - start_memory) / 1024 / 1024:.2f}MB")
```

## 🔧 自定义演示

### 创建自己的演示

你可以基于现有演示创建自己的测试：

```python
#!/usr/bin/env python3
"""
自定义演示脚本
"""

from src.interfaces.cli import AIDefectDetectorCLI

def custom_demo():
    # 你的自定义逻辑
    cli = AIDefectDetectorCLI()

    # 自定义分析
    results = cli.analyze_project(
        path="./your_code",
        mode="static",
        options={"tools": ["pylint", "bandit"]}
    )

    # 自定义处理
    process_results(results)

if __name__ == "__main__":
    custom_demo()
```

### 扩展现有演示

可以修改现有演示来测试特定功能：

```python
# 在demo_t018_static_analysis.py中添加
def test_custom_rules():
    # 测试自定义规则
    pass

# 修改主函数调用
if __name__ == "__main__":
    run_original_demo()
    test_custom_rules()
```

## 📚 学习资源

### 文档
- [快速开始指南](QUICKSTART.md)
- [项目概览](OVERVIEW.md)
- [完整文档](README.md)

### 源码
- 查看 `src/` 目录了解实现细节
- 查看 `tests/` 目录了解测试用例
- 查看 `web/` 目录了解前端实现

### 社区
- 提交Issue报告问题
- 贡献代码和文档
- 分享使用经验

---

**🎭 通过这些演示，你将全面了解AIDefectDetector的强大功能！**