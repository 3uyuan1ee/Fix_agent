# AIDefectDetector

基于AI Agent的软件项目缺陷自主检测与修复系统

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-904%20passed-brightgreen.svg)](tests/)

## 🚀 项目简介

AIDefectDetector是一个智能化的代码缺陷检测与修复系统，基于AI Agent架构开发，能够自主理解项目上下文、利用工具进行分析、制定决策并执行修复任务。系统采用模块化设计，支持多种分析模式和交互界面。

## ✨ 核心特性

### 🤖 三种智能工作模式
- **静态分析模式** (Static)：基于传统工具进行快速代码质量、安全和风格检查
- **深度分析模式** (Deep)：结合大语言模型提供智能代码分析和深度洞察
- **分析修复模式** (Fix)：智能检测代码问题并提供自动修复建议

### 🖥️ 双界面支持
- **命令行界面** (CLI)：适合开发者和自动化脚本
- **Web界面** (Web)：直观的可视化操作界面，支持拖拽上传

### 🧰 丰富的分析工具
- **AST语法分析器**：深度解析代码结构
- **Pylint代码质量检查**：全面的代码质量评估
- **Flake8代码风格检查**：PEP8风格规范检查
- **Bandit安全漏洞检测**：常见安全问题扫描

### 🎯 智能化功能
- **智能文件选择**：根据用户需求自动选择相关文件
- **上下文理解**：基于项目结构提供更精准的分析
- **专业代码对比**：直观显示修复前后的代码差异
- **进度追踪**：实时显示分析进度和结果
- **结果导出**：支持JSON、CSV、HTML等多种格式导出

## 📁 项目结构

```
AIDefectDetector/
├── src/                    # 核心源代码
│   ├── agent/             # AI Agent核心模块
│   │   ├── orchestrator.py    # 任务编排器
│   │   ├── planner.py        # 任务规划器
│   │   ├── execution_engine.py # 执行引擎
│   │   └── mode_router.py     # 模式路由器
│   ├── interfaces/        # 用户界面
│   │   ├── cli.py           # 命令行界面
│   │   └── web.py          # Web界面
│   ├── tools/            # 分析工具
│   │   ├── ast_analyzer.py    # AST分析器
│   │   ├── pylint_analyzer.py # Pylint分析器
│   │   ├── flake8_analyzer.py # Flake8分析器
│   │   └── bandit_analyzer.py # Bandit分析器
│   ├── llm/              # 大语言模型集成
│   ├── utils/            # 工具模块
│   └── prompts/          # 提示词模板
├── web/                   # Web前端资源
│   ├── templates/        # HTML模板
│   └── static/          # 静态资源
├── tests/                # 测试代码
├── config/               # 配置文件
├── docs/                 # 文档
└── main.py              # 程序入口
```

## 🛠️ 快速开始

### 环境要求

- Python 3.8+
- 推荐使用虚拟环境

### ⚡ 一键安装（推荐）

#### Linux/macOS
```bash
# 克隆项目
git clone <repository-url>
cd AIDefectDetector

# 一键安装到全局
./install.sh
```

#### Windows
```batch
# 克隆项目
git clone <repository-url>
cd AIDefectDetector

# 一键安装到全局
install.bat
```

### 🚀 使用全局命令

安装完成后，可以在任何目录下使用：

```bash
# 查看帮助
aidefect --help

# 静态分析（快速，不消耗API额度）
aidefect analyze static ./your-project

# 深度分析（智能，需要API密钥）
aidefect analyze deep ./your-project

# 分析修复（提供修复建议）
aidefect analyze fix ./your-project

# 启动Web界面
aidefect-web
```

### 🔧 手动安装

如果自动安装失败，可以手动安装：

1. **克隆项目**
```bash
git clone <repository-url>
cd AIDefectDetector
```

2. **创建虚拟环境**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **安装到全局**
```bash
pip install -e .
```

5. **配置API密钥**
```bash
# 复制配置模板
cp config/user_config.example.yaml config/user_config.yaml

# 编辑配置文件，添加你的API密钥
# 支持OpenAI、Anthropic、智谱AI等多个厂商
```

### 运行系统

#### 命令行模式
```bash
# 全局命令（推荐）
aidefect
aidefect --help

# 或传统方式
python main.py
python main.py --help
```

#### Web界面模式
```bash
# 全局命令（推荐）
aidefect-web

# 或传统方式
python main.py web

# 访问界面
# 浏览器打开：http://localhost:5000
```

Web界面功能包括：
- 📁 项目文件上传
- 🔍 实时分析进度显示
- 📊 可视化结果展示
- 🔧 修复建议查看
- 📤 结果导出功能

## 📖 使用示例

### 基础用法

```python
# 导入并使用
from src.interfaces.web import AIDefectDetectorWeb

# 创建Web应用实例
app = AIDefectDetectorWeb()

# 启动服务
app.run(host='127.0.0.1', port=5000)
```

### 高级配置

```yaml
# config/user_config.yaml
llm:
  provider: "openai"  # openai, anthropic, zhipu
  api_key: "your-api-key"
  model: "gpt-4"

static_analysis:
  tools: ["pylint", "flake8", "bandit", "ast"]
  parallel: true
  timeout: 300

web:
  host: "127.0.0.1"
  port: 5000
  debug: false
```

## 🧪 测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定模块测试
python -m pytest tests/test_tools/ -v

# 运行Web界面测试
python -m pytest tests/test_t031_fix_interface.py -v

# 查看测试覆盖率
python -m pytest --cov=src tests/
```

测试覆盖情况：
- ✅ **904个测试用例通过**
- ✅ **T031修复操作界面全部测试通过**
- ✅ **核心功能测试覆盖完整**
：

### ✅ 已实现功能
- **代码对比显示**：专业的diff-viewer组件，支持行级对比
- **确认和取消按钮**：Bootstrap模态框，安全确认机制
- **修复进度显示**：实时进度追踪，步骤化展示
- **修复结果摘要**：详细的修复报告和统计信息

### 🔧 界面特性
- 响应式设计，支持移动端
- 专业的代码差异可视化
- 详细的修复步骤追踪
- 多格式结果导出（JSON、TXT、DIFF）

## 📊 性能特点

- **快速静态分析**：毫秒级响应，不消耗API额度
- **智能深度分析**：结合AI的深度代码理解
- **并行处理**：多文件并行分析，提升效率
- **缓存机制**：智能缓存，避免重复分析
- **增量分析**：仅分析变更文件，节省时间

## 🤝 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 开发规范

- 遵循PEP8代码规范
- 编写单元测试
- 更新相关文档
- 通过所有测试用例

## 📝 更新日志

### v1.0.0 (2025-10-19)
- ✅ 完成三种工作模式实现
- ✅ 完成Web界面开发
- ✅ 完成T031修复操作界面
- ✅ 904个测试用例全部通过
- ✅ 支持多厂商大语言模型集成

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情