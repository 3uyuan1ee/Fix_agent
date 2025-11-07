# Fix_agent - 智能代码修复和项目分析系统

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/3uyuan1ee/fix-agent)

Fix_agent是一个基于多Agent协作的智能代码修复和项目分析系统，采用分层Agent架构和感知-决策-执行模型，提供全面的代码质量管理和项目维护功能。

## ✨ 核心特性

### 🤖 多Agent协作架构
- **协调层Agent**: Manager Agent（工作流协调）、Verifier Agent（验证协调）
- **分析层Agent**: Analyzer Agent（问题感知和初步分析）
- **专业层Agent**: Architect、Logic、Performance、Security、Test等专项Agent
- **支持层Agent**: Knowledge Agent（知识管理）、Report Agent（报告生成）

### 🔧 智能工具系统
- **感知类工具**: 项目感知、代码感知、问题感知
- **决策类工具**: 问题分析、任务规划决策
- **执行类工具**: 代码修复、测试执行
- **工具生态**: 支持自定义工具和第三方集成

### 🔄 工作流引擎
- 状态机驱动的流程管理
- 任务队列和依赖管理
- 支持暂停、恢复、回滚
- 可配置工作流定义

### 🧠 LLM集成
- Zhipu AI、OpenAI等多种LLM支持
- LangChain框架集成
- 智能代码分析和修复建议
- 上下文感知的对话模式

### 📊 全面分析能力
- **架构分析**: 设计模式检测、架构验证、改进建议
- **逻辑分析**: 业务规则检测、控制流分析、逻辑问题修复
- **性能分析**: 瓶颈检测、优化建议、性能监控
- **安全分析**: 漏洞扫描、合规检查、安全修复
- **测试分析**: 用例生成、覆盖率分析、质量评估

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/fix-agent/fix-agent.git
cd fix-agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 开发模式安装
pip install -e .
```

### 基础使用

```bash
# 初始化项目
fix-agent init

# 运行完整工作流
fix-agent workflow

# 启动对话模式
fix-agent chat

# 查看帮助
fix-agent --help
```

### 配置

创建配置文件 `config/default.yaml`:

```yaml
# LLM配置
llm:
  provider: "zhipu"  # 支持 zhipu, openai
  api_key: "your-api-key"
  model: "chatglm3-130b"
  temperature: 0.7
  max_tokens: 4000

# Agent配置
agents:
  max_concurrent: 5
  heartbeat_interval: 30.0
  timeout: 60.0

# 工具配置
tools:
  static_analysis:
    enabled: true
    tools: ["pylint", "flake8", "bandit"]
  backup_enabled: true
  validation_enabled: true
```

## 📁 项目结构

```
fix-agent/
├── src/                    # 源代码
│   ├── agent/             # Agent实现
│   ├── tools/             # 工具系统
│   ├── llm/               # LLM集成
│   ├── interfaces/        # 用户界面
│   ├── config/            # 配置管理
│   └── utils/             # 工具类
├── tests/                 # 测试代码
├── config/                # 配置文件
├── docs/                  # 文档
├── web/                   # Web界面
└── scripts/               # 脚本工具
```

## 🔧 开发

### 环境设置

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 安装pre-commit钩子
pre-commit install

# 运行测试
pytest

# 代码格式化
black src/ tests/
isort src/ tests/

# 类型检查
mypy src/

# 代码质量检查
flake8 src/
pylint src/
```

### 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_agent/

# 生成覆盖率报告
pytest --cov=src --cov-report=html

# 运行集成测试
pytest tests/test_integration/ -m integration
```

## 📖 文档

- [用户手册](docs/user_guide.md)
- [开发指南](docs/developer_guide.md)
- [API文档](docs/api_reference.md)
- [架构设计](docs/architecture.md)
- [贡献指南](CONTRIBUTING.md)

## 🤝 贡献

我们欢迎所有形式的贡献！请查看 [贡献指南](CONTRIBUTING.md) 了解详情。

### 开发流程

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。


## 📞 联系我们

- 项目主页: https://github.com/3uyuan1ee/fix-agent
- 文档网站: https://fix-agent.readthedocs.io/
- 问题反馈: https://github.com/3uyuan1ee/fix-agent/issues
- 邮箱: 1481059602@qq.com
