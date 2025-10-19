# 🚀 AIDefectDetector 快速开始指南

5分钟内快速上手AIDefectDetector，体验智能代码缺陷检测与修复！

## ⚡ 5分钟快速体验

### 1️⃣ 环境准备 (1分钟)

```bash
# 检查Python版本（需要3.8+）
python --version

# 如果版本不满足，请升级Python或使用虚拟环境
```

### 2️⃣ 安装系统 (2分钟)

```bash
# 克隆项目
git clone <repository-url>
cd AIDefectDetector

# 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3️⃣ 基础配置 (1分钟)

```bash
# 复制配置文件
cp config/user_config.example.yaml config/user_config.yaml

# 编辑配置文件，添加你的API密钥（可选，静态分析不需要）
# 支持OpenAI、Anthropic、智谱AI等
```

### 4️⃣ 启动体验 (1分钟)

#### 🌐 Web界面体验（推荐）

```bash
# 启动Web服务
python main.py web

# 浏览器访问
http://localhost:5000
```

Web界面功能：
- 📁 拖拽上传项目文件
- 🔍 选择分析模式（静态/深度/修复）
- 📊 实时查看分析进度
- 📋 查看详细分析结果
- 🔧 查看修复建议
- 📤 导出分析报告

#### 💻 命令行体验

```bash
# 快速静态分析（无需API密钥）
python main.py analyze static ./src

# 深度分析（需要API密钥）
python main.py analyze deep ./src

# 修复分析（需要API密钥）
python main.py analyze fix ./src
```

## 🎯 三种模式快速体验

### 📊 静态分析模式（零成本，秒级响应）

**适用场景**：日常代码检查、CI/CD集成

```bash
# 分析整个项目
python main.py analyze static /path/to/your/project

# 分析特定文件
python main.py analyze static ./src/main.py

# 查看帮助
python main.py --help
```

**特点**：
- ⚡ 速度快（毫秒级）
- 💰 零成本（不消耗API额度）
- 🔍 全面检查（语法、质量、安全、风格）
- 📊 详细报告

### 🧠 深度分析模式（AI智能分析）

**适用场景**：代码重构、架构分析、技术债务评估

```bash
# 配置API密钥后使用
python main.py analyze deep /path/to/your/project

# 交互式深度分析
python main.py analyze deep ./src --interactive
```

**特点**：
- 🤖 AI智能分析
- 🔍 深度代码理解
- 💡 详细改进建议
- 📝 可读性强的报告

### 🔧 修复分析模式（智能修复建议）

**适用场景**：代码质量改进、安全漏洞修复

```bash
# 获取修复建议
python main.py analyze fix /path/to/your/project

# 自动应用修复（谨慎使用）
python main.py analyze fix ./src --auto-fix
```

**特点**：
- 🛠️ 智能修复建议
- 🔒 安全确认机制
- 📋 详细修复步骤
- 💾 自动备份保护

## 📋 常用命令速查

### Web界面操作

| 功能 | 操作说明 |
|------|----------|
| 上传项目 | 拖拽文件到上传区域 |
| 选择模式 | 静态/深度/修复三种模式 |
| 开始分析 | 点击"开始分析"按钮 |
| 查看结果 | 在结果页面查看详细报告 |
| 导出报告 | 支持JSON、CSV、HTML格式 |

### 命令行操作

```bash
# 基础命令
python main.py                    # 显示帮助
python main.py web                # 启动Web界面
python main.py analyze static .   # 静态分析当前目录
python main.py analyze deep .     # 深度分析当前目录
python main.py analyze fix .      # 修复分析当前目录

# 高级选项
python main.py analyze static . --output results.json  # 输出到文件
python main.py analyze deep . --model gpt-4           # 指定模型
python main.py analyze static . --verbose             # 详细输出
python main.py analyze static . --parallel           # 并行分析
```

## 🔧 配置说明

### 基础配置文件

```yaml
# config/user_config.yaml
llm:
  provider: "openai"        # 可选: openai, anthropic, zhipu
  api_key: "your-api-key"   # 你的API密钥
  model: "gpt-4"           # 模型名称

static_analysis:
  tools: ["pylint", "flake8", "bandit", "ast"]  # 使用的工具
  parallel: true           # 并行分析
  timeout: 300            # 超时时间（秒）

web:
  host: "127.0.0.1"       # 监听地址
  port: 5000              # 监听端口
  debug: false            # 调试模式
```

### API密钥配置

#### OpenAI
```yaml
llm:
  provider: "openai"
  api_key: "sk-..."
  model: "gpt-4"
  base_url: "https://api.openai.com/v1"
```

#### Anthropic Claude
```yaml
llm:
  provider: "anthropic"
  api_key: "sk-ant-..."
  model: "claude-3-opus-20240229"
```

#### 智谱AI
```yaml
llm:
  provider: "zhipu"
  api_key: "your-zhipu-key"
  model: "glm-4"
```

## 🎯 实际使用场景

### 场景1：日常代码检查

```bash
# 每天代码提交前检查
python main.py analyze static ./src

# 生成质量报告
python main.py analyze static ./src --output daily_report.json
```

### 场景2：代码重构准备

```bash
# 深度分析代码结构
python main.py analyze deep ./src --interactive

# 获取重构建议
python main.py analyze deep ./legacy_code --model gpt-4
```

### 场景3：安全漏洞修复

```bash
# 检测安全问题
python main.py analyze fix ./src

# 查看修复建议
python main.py analyze fix ./src --detailed-report
```

### 场景4：CI/CD集成

```bash
# 持续集成脚本
#!/bin/bash
python main.py analyze static ./src --output ci_report.json
python -c "import json; data=json.load(open('ci_report.json')); exit(1 if data['critical_issues'] > 0 else 0)"
```

## 🚨 常见问题解决

### 问题1：导入错误

```bash
# 确保在虚拟环境中
source .venv/bin/activate

# 重新安装依赖
pip install -r requirements.txt
```

### 问题2：API密钥无效

```bash
# 检查配置文件
cat config/user_config.yaml

# 确保API密钥格式正确
# 测试API连接
python -c "from src.llm.client import LLMClient; client=LLMClient(); print('API连接成功')"
```

### 问题3：分析速度慢

```bash
# 使用并行分析
python main.py analyze static ./src --parallel

# 限制分析文件数量
python main.py analyze static ./src --max-files 50
```

### 问题4：Web界面无法访问

```bash
# 检查端口占用
lsof -i :5000

# 使用不同端口
python -c "
from src.interfaces.web import AIDefectDetectorWeb
app = AIDefectDetectorWeb()
app.run(port=8080)
"
```

## 📚 更多资源

### 📖 详细文档
- [完整README](README.md) - 详细项目介绍
- [API文档](docs/api.md) - API接口说明
- [配置指南](docs/configuration.md) - 配置详细说明

### 🧪 示例代码
- [demo/](demo/) 目录包含各种使用示例
- [tests/](tests/) 目录包含测试用例

### 🤝 社区支持
- 提交Issue报告问题
- 提交Pull Request贡献代码
- 查看Wiki获取更多信息

## 🎉 开始你的智能代码分析之旅！

现在你已经掌握了AIDefectDetector的基础使用方法：

1. **静态分析** - 日常代码质量检查
2. **深度分析** - AI智能代码分析
3. **修复分析** - 智能修复建议

选择适合你的模式，开始体验智能代码分析的强大功能吧！

---

**💡 提示**：建议先使用静态分析模式熟悉系统，再探索深度分析和修复功能。

**🔗 相关链接**：
- [GitHub仓库](https://github.com/your-repo/AIDefectDetector)
- [在线文档](https://your-docs-site.com)
- [问题反馈](https://github.com/your-repo/AIDefectDetector/issues)