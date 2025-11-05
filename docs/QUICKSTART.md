# 🚀 AIDefectDetector 快速开始指南

5分钟内快速上手AIDefectDetector，体验智能代码缺陷检测与修复！

## 📋 项目概览

AIDefectDetector是一个基于AI Agent的智能代码缺陷检测与修复系统，支持**四种工作模式**：

- **静态分析模式** - 基于传统工具的快速代码检查（无需API密钥）
- **深度分析模式** - AI智能代码分析和改进建议（需要API密钥）
- **修复分析模式** - AI驱动的问题检测和自动修复（需要API密钥）
- **工作流修复模式** - 完整的B→C→D→E→F/G→H→I→J/K→L→B/M AI修复工作流（需要API密钥）

## ⚡ 5分钟快速体验

### 1️⃣ 环境准备 (1分钟)

```bash
# 检查Python版本（需要3.8+）
python3 --version

# 如果版本不满足，请升级Python或使用虚拟环境
python3 -m venv aidefect_env
source aidefect_env/bin/activate  # Linux/macOS
# aidefect_env\Scripts\activate  # Windows
```

### 2️⃣ 安装系统 (2分钟)

#### Unix/Linux/macOS 用户：
```bash
# 克隆项目
git clone <repository-url>
cd AIDefectDetector

# 运行统一安装脚本
bash scripts/install_unix.sh
```

#### Windows 用户：
```bash
# 克隆项目
git clone <repository-url>
cd AIDefectDetector

# 运行统一安装脚本
scripts\install_windows.bat
```

安装脚本会自动：
- ✅ 检查Python环境和依赖
- ✅ 创建虚拟环境并安装依赖
- ✅ 创建全局命令链接
- ✅ 生成基础配置文件

### 3️⃣ 配置API密钥 (1分钟)

```bash
# 运行LLM配置向导（推荐）
python3 scripts/configure_llm.py

# 或快速配置模式
python3 scripts/configure_llm.py --quick

# 或直接配置智谱AI（推荐国内用户）
python3 scripts/configure_llm.py --provider zhipu
```

支持以下LLM提供商：
- 🇨🇳 **智谱AI** - 推荐国内用户，访问稳定
- 🌐 **OpenAI** - 功能强大，需要代理
- 🤖 **Anthropic** - 推理能力强，需要代理

### 4️⃣ 启动体验 (1分钟)

#### 🌐 Web界面体验（推荐）

```bash
# 启动Web服务
python3 main.py web

# 浏览器访问
http://localhost:5000
```

Web界面功能：
- 📁 拖拽上传项目文件
- 🔍 选择分析模式（静态/深度/修复/工作流）
- 📊 实时查看分析进度
- 📋 查看详细分析结果
- 🔧 查看修复建议
- 📤 导出分析报告

#### 💻 命令行体验

```bash
# 静态分析（无需API密钥）
python3 main.py analyze static ./src

# 深度分析（需要API密钥）
python3 main.py analyze deep ./src

# 修复分析（需要API密钥）
python3 main.py analyze fix ./src

# 工作流修复（需要API密钥，推荐）
python3 main.py analyze workflow ./src
```

## 🎯 四种模式快速体验

### 📊 静态分析模式（零成本，秒级响应）

**适用场景**：日常代码检查、CI/CD集成

```bash
# 分析整个项目
python3 main.py analyze static /path/to/your/project

# 分析特定文件
python3 main.py analyze static ./src/main.py

# 指定工具分析
python3 main.py analyze static ./src --tools pylint,flake8

# 生成报告
python3 main.py analyze static ./src --output report.json
```

**特点**：
- ⚡ 速度快（毫秒级）
- 💰 零成本（不消耗API额度）
- 🔍 全面检查（语法、质量、安全、风格）
- 📊 详细报告

**支持的工具**：
- `ast` - Python AST语法分析
- `pylint` - 代码质量检查
- `flake8` - 代码风格检查
- `bandit` - 安全漏洞检测

### 🧠 深度分析模式（AI智能分析）

**适用场景**：代码重构、架构分析、技术债务评估

```bash
# 基础深度分析
python3 main.py analyze deep /path/to/your/project

# 详细输出
python3 main.py analyze deep ./src --verbose

# 交互式深度分析
python3 main.py analyze deep ./src --interactive

# 指定模型
python3 main.py analyze deep ./src --model glm-4.5
```

**特点**：
- 🤖 AI智能分析
- 🔍 深度代码理解
- 💡 详细改进建议
- 📝 可读性强的报告
- 🎯 交互式对话

### 🔧 修复分析模式（智能修复建议）

**适用场景**：代码质量改进、安全漏洞修复

```bash
# 获取修复建议
python3 main.py analyze fix /path/to/your/project

# 详细修复报告
python3 main.py analyze fix ./src --detailed-report

# 交互式修复
python3 main.py analyze fix ./src --interactive

# 自动修复（谨慎使用）
python3 main.py analyze fix ./src --no-confirm
```

**特点**：
- 🛠️ 智能修复建议
- 🔒 安全确认机制
- 📋 详细修复步骤
- 💾 自动备份保护

### 🔄 工作流修复模式（完整AI修复流程）⭐

**适用场景**：复杂的代码修复项目、需要完整闭环的场景

**工作流程**：B→C→D→E→F/G→H→I→J/K→L→B/M

```bash
# 启动完整工作流（推荐）
python3 main.py analyze workflow /path/to/your/project

# 详细输出
python3 main.py analyze workflow ./src --verbose

# 导出结果
python3 main.py analyze workflow ./src --output workflow_results.json

# 模拟运行（查看流程但不实际修改）
python3 main.py analyze workflow ./src --dry-run
```

**工作流步骤**：
1. **B节点** - AI问题检测
2. **C节点** - AI修复建议生成
3. **D节点** - 用户审查
4. **E节点** - 用户决策（批准/修改/拒绝）
5. **F/G节点** - 执行修复/跳过问题
6. **H节点** - 修复验证
7. **I节点** - 用户验证决策
8. **J/K节点** - 问题解决/重新分析
9. **L节点** - 检查剩余问题
10. **B/M节点** - 继续分析/工作流完成

**特点**：
- 🔄 完整闭环工作流
- 🤖 AI驱动决策
- 👥 用户协作确认
- 🛡️ 安全备份机制
- 📊 详细流程追踪

## 📋 常用命令速查

### 基础命令

```bash
# 主入口命令
python3 main.py                    # 显示帮助
python3 main.py web                # 启动Web界面

# 分析命令
python3 main.py analyze static .   # 静态分析当前目录
python3 main.py analyze deep .     # 深度分析当前目录
python3 main.py analyze fix .      # 修复分析当前目录
python3 main.py analyze workflow . # 工作流修复（推荐）

# 帮助命令
python3 main.py --help             # 显示完整帮助
python3 main.py analyze --help      # 显示分析命令帮助
```

### 高级选项

```bash
# 输出选项
python3 main.py analyze static . --output results.json
python3 main.py analyze static . --format json
python3 main.py analyze static . --export analysis.json

# 工具选择
python3 main.py analyze static . --tools pylint,bandit
python3 main.py analyze deep . --model gpt-4

# 交互控制
python3 main.py analyze deep . --interactive
python3 main.py analyze fix . --no-confirm
python3 main.py analyze static . --dry-run

# 工作流特定选项
python3 main.py analyze workflow . --verbose
python3 main.py analyze workflow . --output workflow.json
python3 main.py analyze workflow . --dry-run
```

### 配置管理命令

```bash
# LLM配置向导
python3 scripts/configure_llm.py                      # 交互式配置
python3 scripts/configure_llm.py --quick              # 快速配置
python3 scripts/configure_llm.py --provider zhipu     # 配置智谱AI
python3 scripts/configure_llm.py --provider openai    # 配置OpenAI
python3 scripts/configure_llm.py --provider anthropic # 配置Anthropic

# 配置管理
python3 scripts/configure_llm.py --status             # 查看配置状态
python3 scripts/configure_llm.py --diagnose           # 配置诊断
python3 scripts/configure_llm.py --test zhipu         # 测试智谱AI连接
```

## 🔧 配置说明

### 配置文件位置

系统会自动创建配置文件：
- **用户配置**: `~/.aidefect/config.yaml`
- **环境变量**: `~/.aidefect/.env`
- **LLM配置**: `config/llm_config.yaml`

### API密钥配置

#### 智谱AI（推荐国内用户）
```bash
# 临时设置
export ZHIPU_API_KEY="your-api-key"

# 永久设置（添加到 ~/.bashrc 或 ~/.zshrc）
echo 'export ZHIPU_API_KEY="your-api-key"' >> ~/.bashrc
source ~/.bashrc

# 或使用配置脚本
python3 scripts/configure_llm.py --provider zhipu
```

#### OpenAI
```bash
export OPENAI_API_KEY="your-openai-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 如需代理则修改
```

#### Anthropic Claude
```bash
export ANTHROPIC_API_KEY="your-anthropic-key"
export ANTHROPIC_BASE_URL="https://api.anthropic.com"
```

### 配置文件示例

编辑 `~/.aidefect/config.yaml`：

```yaml
# LLM提供商配置
llm:
  default_provider: "zhipu"        # 默认提供商
  zhipu:
    api_key: "${ZHIPU_API_KEY}"
    model: "glm-4.5"
    api_base: "https://open.bigmodel.cn/api/paas/v4/"
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4"
    base_url: "${OPENAI_BASE_URL:https://api.openai.com/v1}"

# 分析配置
analysis:
  static:
    tools: ["ast", "pylint", "flake8", "bandit"]
    parallel: true
    timeout: 300
  deep:
    max_file_size: 100000
    temperature: 0.3
    max_tokens: 4000
  fix:
    backup_enabled: true
    auto_confirm: false
  workflow:
    backup_enabled: true
    auto_save_progress: true

# Web界面配置
web:
  host: "127.0.0.1"
  port: 5000
  debug: false
```

## 🎯 实际使用场景

### 场景1：日常代码检查

```bash
# 每天代码提交前检查
python3 main.py analyze static ./src

# 生成质量报告
python3 main.py analyze static ./src --output daily_report.json

# CI/CD集成
python3 main.py analyze static ./src --format json --output ci_results.json
```

### 场景2：代码重构准备

```bash
# 深度分析代码结构
python3 main.py analyze deep ./src --interactive

# 获取重构建议
python3 main.py analyze deep ./legacy_code --model gpt-4

# 分析特定模块
python3 main.py analyze deep ./src/utils/config.py --verbose
```

### 场景3：复杂修复项目（推荐使用工作流模式）

```bash
# 启动完整工作流修复
python3 main.py analyze workflow ./src

# 详细流程追踪
python3 main.py analyze workflow ./src --verbose

# 导出完整修复报告
python3 main.py analyze workflow ./src --output complete_fix_report.json
```

### 场景4：安全漏洞修复

```bash
# 使用工作流模式修复安全问题
python3 main.py analyze workflow ./src --focus security

# 或者使用修复模式
python3 main.py analyze fix ./src --focus security
```

### 场景5：项目质量评估

```bash
# 综合质量报告
python3 main.py analyze static ./src --format html --output quality_report.html

# 深度质量分析
python3 main.py analyze deep ./src --model gpt-4 --verbose

# 工作流模式全面改进
python3 main.py analyze workflow ./src --output improvement_plan.json
```

## 🔄 工作流模式详解

工作流模式是系统的核心功能，实现了完整的AI驱动修复流程：

### 工作流图示
```
Phase A完成 → B:AI问题检测 → C:修复建议 → D:用户审查 → E:用户决策
      ↑                                                      ↓
      M:工作流完成 ← L:检查剩余 ← J:问题解决 ← I:验证决策 ← H:修复验证
      ↓                                                      ↑
重新分析 ← K:重新分析 ← G:跳过问题 ← F:执行修复 ← E:用户决策
```

### 工作流特点
- 🤖 **AI驱动**：问题检测和修复建议完全由AI完成
- 👥 **用户协作**：关键决策点需要用户确认
- 🔄 **闭环流程**：从问题发现到修复验证的完整闭环
- 🛡️ **安全保护**：自动备份和回滚机制
- 📊 **流程追踪**：详细记录每个步骤的执行情况

### 适用场景
- 复杂的代码重构项目
- 需要多轮迭代修复的场景
- 对修复质量要求极高的项目
- 需要详细修复记录的合规项目

## 🚨 常见问题解决

### 问题1：导入错误

```bash
# 确保在项目目录中
cd /path/to/AIDefectDetector

# 重新激活虚拟环境
source ~/.aidefect_venv/bin/activate  # 或aidefect_env/bin/activate

# 重新安装依赖
pip install -r requirements.txt
```

### 问题2：API密钥无效

```bash
# 检查配置状态
python3 scripts/configure_llm.py --status

# 测试API连接
python3 scripts/configure_llm.py --test zhipu

# 重新配置
python3 scripts/configure_llm.py --provider zhipu
```

### 问题3：工作流模式卡住

```bash
# 使用详细输出查看状态
python3 main.py analyze workflow ./src --verbose

# 检查工作流状态文件
ls -la .fix_backups/

# 使用模拟运行预览流程
python3 main.py analyze workflow ./src --dry-run
```

### 问题4：分析速度慢

```bash
# 使用并行分析
python3 main.py analyze static ./src --parallel

# 限制分析文件数量
python3 main.py analyze static ./src --max-files 50

# 使用特定工具
python3 main.py analyze static ./src --tools ast,pylint
```

### 问题5：Web界面无法访问

```bash
# 检查端口占用
lsof -i :5000

# 使用不同端口
python3 -c "
from src.interfaces.web import app
app.run(host='127.0.0.1', port=8080, debug=True)
"
```

## 📚 更多资源

### 📖 详细文档
- [安装指南](docs/Guide/INSTALL_GUIDE.md) - 完整安装说明
- [API配置指南](docs/Guide/API_CONFIG_GUIDE.md) - LLM配置详细说明
- [项目架构](../README.md) - 详细项目介绍

### 🧪 示例和测试
- [示例项目](../example/) - 包含各种代码问题的测试用例
- [工作流备份](../.fix_backups/) - 工作流执行记录和备份

### 🤝 获取帮助

```bash
# 运行配置诊断
python3 scripts/configure_llm.py --diagnose

# 查看详细帮助
python3 main.py --help
python3 main.py analyze --help
python3 main.py analyze workflow --help

# 启动交互模式
python3 main.py analyze deep . --interactive
```

## 🎉 开始你的智能代码分析之旅！

现在你已经掌握了AIDefectDetector的四种工作模式：

1. **静态分析** - 日常代码质量检查（零成本）
2. **深度分析** - AI智能代码分析（需要API密钥）
3. **修复分析** - 智能修复建议（需要API密钥）
4. **工作流修复** - 完整AI修复流程（需要API密钥，推荐）

推荐使用流程：
1. 先使用静态分析熟悉系统
2. 配置API密钥体验深度分析
3. 尝试修复分析功能
4. 使用工作流模式处理复杂修复项目

选择适合你的模式，开始体验智能代码分析的强大功能吧！

---

**💡 提示**：工作流模式是最强大的功能，推荐在重要修复项目中使用。

**🔗 快速命令参考**：
- 安装：`bash scripts/install_unix.sh` / `scripts\install_windows.bat`
- 配置：`python3 scripts/configure_llm.py --quick`
- 静态分析：`python3 main.py analyze static ./src`
- 深度分析：`python3 main.py analyze deep ./src`
- 修复分析：`python3 main.py analyze fix ./src`
- 工作流修复：`python3 main.py analyze workflow ./src`