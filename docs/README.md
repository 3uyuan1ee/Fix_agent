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

## 🏗️ 项目结构

```
AIDefectDetector/
├── main.py                 # 主程序入口
├── src/                    # 核心源代码
│   ├── agent/             # Agent核心逻辑
│   ├── interfaces/        # 接口层（CLI/Web）
│   ├── llm/              # LLM集成模块
│   ├── tools/            # 工具集成模块
│   └── utils/            # 工具类（配置、日志、缓存等）
├── config/                # 配置文件
│   ├── examples/         # 配置模板
│   ├── default.yaml      # 默认配置
│   └── user_config.yaml  # 用户配置
├── scripts/               # 配置和管理脚本 ⭐
│   ├── quick_setup.py    # 🚀 快速设置向导
│   ├── manage_config.py  # 🔧 配置管理工具
│   ├── diagnose_config.py # 🔍 配置诊断工具
│   ├── setup_api.sh      # 📋 API配置向导
│   └── set_zhipu_key.sh  # ⚡ 智谱AI快速配置
├── tools/                 # 辅助工具
│   ├── aidefect_cli.py   # CLI工具
│   ├── aidefect_web.py   # Web工具
│   └── setup.py          # 安装脚本
├── demos/                 # 演示和示例
│   ├── simple_demo.py    # 简单演示
│   └── demo_cli.py       # CLI演示
├── docs/                  # 文档 📚
│   ├── API_CONFIG_GUIDE.md     # API配置详细指南
│   ├── CONFIG_IMPROVEMENTS.md  # 配置改进总结
│   ├── QUICK_START.md          # 快速开始指南
│   └── T026_DEEP_ANALYSIS_TASKS.md # 深度分析任务
├── tests/                 # 正式测试
├── tests-temp/           # 临时测试文件
└── logs/                 # 日志文件
```

## 🚀 快速开始

### 方法1: 使用快速设置向导（推荐新手）

```bash
# 运行快速设置向导
python3 scripts/quick_setup.py

# 按提示选择配置方式并设置API密钥
```

### 方法2: 使用配置脚本

```bash
# 智谱AI快速配置（推荐国内用户）
./scripts/set_zhipu_key.sh

# 或使用完整配置向导
./scripts/setup_api.sh
```

### 方法3: 手动配置

```bash
# 1. 应用配置模板
python3 scripts/manage_config.py apply minimal

# 2. 设置API密钥
export ZHIPU_API_KEY="your-api-key"

# 3. 验证配置
python3 scripts/diagnose_config.py
```

## 🎯 使用示例

### 深度分析

```bash
# 分析单个文件
python3 main.py analyze deep src/utils/config.py

# 详细输出
python3 main.py analyze deep src/utils/config.py --verbose

# 分析整个目录
python3 main.py analyze deep src/ --verbose
```

### 静态分析

```bash
# 静态分析
python3 main.py analyze static . --dry-run

# 生成报告
python3 main.py analyze static . --output report.json
```

## 🔧 配置管理

### 配置模板

```bash
# 列出所有模板
python3 scripts/manage_config.py list

# 应用开发环境模板
python3 scripts/manage_config.py apply development

# 应用生产环境模板
python3 scripts/manage_config.py apply production
```

### 配置诊断

```bash
# 运行完整诊断
python3 scripts/diagnose_config.py

# 验证当前配置
python3 scripts/manage_config.py validate

# 查看配置状态
python3 scripts/manage_config.py status
```


## 🛠️ 开发

### 环境要求

- Python 3.8+
- 推荐使用虚拟环境

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行测试

```bash
# 运行所有测试
python -m pytest

# 运行特定测试
python -m pytest tests/test_config.py
```

## 📄 许可证

本项目采用 MIT 许可证。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 支持

如果遇到问题：

1. 运行配置诊断：`python3 scripts/diagnose_config.py`
2. 查看配置指南：`cat docs/API_CONFIG_GUIDE.md`
3. 使用设置向导：`python3 scripts/quick_setup.py`