[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MPL2.0-green.svg)](LICENSE)
[![LangChain](https://img.shields.io/badge/LangChain-1.0-brightgreen.svg)](https://python.langchain.com)
[![DeepAgent](https://img.shields.io/badge/DeepAgent-Framework-orange.svg)](https://github.com/3uyuan1ee/Fix_agent)

---
![img](https://github.com/3uyuan1ee/Fix_agent/master/images/Agents_and_Command.gif)

基于Langchian1.0和Deepagents，实现项目问题检测->自动修复->效果验证的闭环
- **智能分析** - 自动识别语法、逻辑、性能和安全缺陷
- **精准修复** - 基于深度分析提供针对性修复方案并在human-in-loop下执行修复
- **自动验证** - 确保修复不破坏现有功能
- **持续学习** - 具备记忆能力，越用越智能

### 与众不同的技术架构

Fix Agent采用Langchain1.0的中间件管道系统，提供6层处理：

```mermaid
graph LR
    A[用户输入] --> B[性能监控]
    B --> C[日志记录]
    C --> D[上下文增强]
    D --> E[分层记忆]
    E --> F[框架默认]
    F --> G[安全检查]
    G --> H[Shell工具]

    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#e8f5e8
    style D fill:#fff3e0
    style E fill:#fce4ec
    style F fill:#f8bbd9
    style G fill:#ff8a80
    style H fill:#a5d6a7
```

确保了代码修复的高效性和安全性，同时提供了智能化的用户体验。

---

### 基于Deepagents的Three-subagents架构

#### 1. 缺陷分析代理 (defect-analyzer)
- **语法分析** - 检测语法错误、类型错误、导入错误
- **逻辑分析** - 识别逻辑漏洞、边界条件处理不当
- **性能分析** - 发现性能瓶颈、资源泄漏问题
- **安全分析** - 检查SQL注入、XSS、权限绕过等安全漏洞

#### 2. 代码修复代理 (code-fixer)
- **智能修复** - 基于分析报告自动生成修复代码
- **策略优化** - 从多个修复方案中选择最优解
- **兼容性保证** - 确保修复不会引入新的问题

#### 3. 修复验证代理 (fix-validator)
- **测试验证** - 运行单元测试和集成测试
- **静态分析** - 验证代码质量标准
- **安全扫描** - 确保修复无安全风险

### 全面的技术栈支持

支持主流编程语言的代码质量分析：
- **Web开发** - JavaScript, TypeScript, HTML, CSS
- **后端开发** - Python, Java, Go, Node.js
- **系统编程** - C, C++, Rust
- **移动开发** - Swift, Kotlin
- **数据科学** - Python, R

### 智能工具生态

- **统一工具链** - 集成pylint, flake8, mypy, bandit, black, eslint等
- **智能聚合** - 语义相似度缺陷聚类分析
- **项目探索** - 结构分析和复杂度评估
- **智能测试** - 自动生成和执行验证测试

---

## 现代化用户体验

### 直观的命令行界面

Fix Agent提供了优雅的终端交互体验：

```bash
# 启动Fix Agent
fixagent

# 智能文件引用
> 分析 @src/main.py 中的性能问题

# 命令系统操作
> /cd src
> /memory view

# Shell命令集成
> !git status
```
![img](https://github.com/3uyuan1ee/Fix_agent/master/images/Commands.gif)

### 双模式支持

**CLI模式** 
- 快速、高效的命令行交互
- 丰富的键盘快捷键和自动补全
- 支持多行输入和编辑器集成



**Web模式** - 直观的图形化界面
- 友好的浏览器界面
- 可视化的代码质量报告

### 人机交互

- **打字机效果** - 动态文本输出增强体验
- **实时进度指示** - 清晰显示处理进度，实时监控Agent的行为，调用工具manual和auto两种模式
- **智能提示系统** - /command建议和补全
- **中断支持** - 随时中断长时间运行的分析

---

## 安全防护


1. **文件安全中间件** - 防止恶意文件访问和路径遍历
2. **命令安全中间件** - 限制Shell命令执行范围，精细的文件和目录访问权限控制
3. **内容安全中间件** - 过滤敏感信息和恶意内容,防止API等信息泄露


---

## 快速开始

### 环境要求

- Python 3.11+
- 支持的操作系统：Windows, macOS, Linux

### 安装

```bash
# 克隆项目
git clone https://github.com/3uyuan1ee/Fix_agent.git
cd Fix_agent

# 安装依赖
pip install -r requirements.txt

# 安装Fix Agent
pip install -e .
```

### 配置
#### Clone
```bash
# 配置环境变量
export OPENAI_API_KEY="your-api-key"

# 或创建.env文件
echo "OPENAI_API_KEY=your-api-key" > .env

#支持自动配置，若检测到为配置，启动会引导进行配置，只需获取API即可

#如需使用国内模型还需配置base_url
OPENAI_API_BASE=https://open.bigmodel.cn/api/paas/v4/

#若要启动联网搜索，还需配置Tavily API Key

TAVILY_API_KEY=your_tavily_api_key_here
```
点这里获取[TAVILY_API](https://www.tavily.com/)

#### PYPI
包已上传到PYPI,支持在python环境下pip一键安装
```
# 建议在虚拟python环境下安装
pip install Fix_agent
```

### 启动使用

```bash
# 启动Fix Agent
fixagent

# 查看帮助
fixagent help

# 列出可用的代理
fixagent list
```

---


## 高级功能

### 记忆系统

Fix Agent具备长期记忆能力，能够：

- **记住项目结构** - 下次分析时无需重新扫描
- **学习修复模式** - 根据历史修复优化建议
- **个性化偏好** - 记住用户的编码风格和偏好

```bash
# 查看记忆内容
/memory view

# 搜索特定问题的记忆
/memory search SQL注入

# 清理记忆内容
/memory clear
```
---

## 技术架构

Fix Agent采用现代化的技术架构：

- **异步处理** - 基于asyncio的高性能异步架构
- **流式处理** - 实时显示分析进度和结果
- **模块化设计** - 插件化的工具和中间件系统，用户可自定义
- **类型安全** - 完整的类型注解和静态检查

### 中间件系统

```mermaid
graph TD
    A[用户输入] --> B[中间件管道系统]
    B --> C[性能监控]
    B --> D[日志记录]
    B --> E[上下文增强]
    B --> F[分层记忆]
    B --> G[框架默认]
    B --> H[安全检查]
    B --> I[Shell工具]
    B --> T[智能工具链]

    T --> T1[代码分析工具]
    T --> T2[静态检查工具]
    T --> T3[格式化工具]
    T --> T4[测试工具]
    T --> T5[安全扫描工具]

    C --> J[三段式代理架构]
    D --> J
    E --> J
    F --> J
    G --> J
    H --> J
    I --> J
    T --> J

    J --> K[缺陷分析代理]
    J --> L[代码修复代理]
    J --> M[修复验证代理]

    K --> N[输出结果]
    L --> N
    M --> N

    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style J fill:#e8f5e8
    style N fill:#fff3e0
    style T fill:#ffecb3
    style T1 fill:#fff8e1
    style T2 fill:#fff8e1
    style T3 fill:#fff8e1
    style T4 fill:#fff8e1
    style T5 fill:#fff8e1
```
---

## 贡献指南

我们欢迎社区贡献！您可以通过以下方式参与：

### 报告问题
- 在Issues中报告bug
- 提供详细的重现步骤
- 附上相关的日志信息
- 或联系[我](1481059602@qq.com)

### 功能建议
- 提出新功能想法
- 讨论实现方案
- 提供用户反馈

### 代码贡献
1. Fork项目
2. 创建功能分支
3. 提交Pull Request
4. 参与代码审查

### 文档改进
- 改进用户文档
- 添加使用示例
- 翻译多语言版本


## 许可证

本项目采用MIT许可证，详见[LICENSE](LICENSE)文件。

---

## 联系我

- **GitHub**: https://github.com/3uyuan1ee/Fix_agent
- **Issues**: https://github.com/3uyuan1ee/Fix_agent/issues
- **3uyuan1ee**: 1481059602@qq.com

---

## 致谢

感谢所有为Fix Agent项目做出贡献的开发者和用户。特别感谢开源社区提供的优秀工具和库，让这个项目成为可能。

