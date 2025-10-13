# AIDefectDetector

基于AI Agent的软件项目缺陷自主检测与修复系统

## 项目简介

AIDefectDetector是一个智能化的代码缺陷检测与修复系统，基于LangChain框架开发，能够自主理解项目上下文、利用工具进行分析、制定决策并执行修复任务。

## 功能特性

- **三种工作模式**：
  - 静态分析模式：不调用大模型，基于传统工具进行代码分析
  - 深度分析模式：调用大模型，提供智能代码分析建议
  - 分析修复模式：调用大模型并提供代码修复功能

- **双界面支持**：
  - 命令行界面（CLI）
  - Web界面

- **智能文件选择**：根据用户需求自动选择相关文件进行分析

- **多种分析工具**：
  - AST语法分析
  - Pylint代码质量检查
  - Flake8代码风格检查
  - Bandit安全漏洞检测

## 安装说明

```bash
# 克隆项目
git clone <repository-url>
cd AIDefectDetector

# 安装依赖
pip install -r requirements.txt

# 运行系统
python main.py  # CLI模式
python main.py web  # Web模式
```

## 使用方法

### CLI模式

```bash
# 静态分析
python main.py analyze static /path/to/project

# 深度分析
python main.py analyze deep /path/to/project

# 分析修复
python main.py analyze fix /path/to/project
```

### Web模式

```bash
# 启动Web服务
python main.py web

# 访问 http://localhost:5000
```

## 配置说明

在 `config/` 目录下配置：
- API密钥
- 分析参数
- 缓存设置

## 开发状态

项目正在开发中，当前完成基础框架搭建。

## 许可证

MIT License