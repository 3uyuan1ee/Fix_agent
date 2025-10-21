
## 📁 项目结构

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


## 📚 文档

- **[API配置指南](docs/API_CONFIG_GUIDE.md)** - 详细的API配置说明
- **[快速开始](docs/QUICK_START.md)** - 快速上手指南
- **[配置改进总结](docs/CONFIG_IMPROVEMENTS.md)** - 配置系统改进说明

## 🔑 支持的LLM提供商

| 提供商 | 推荐场景 | 特点 |
|--------|----------|------|
| 智谱AI | 国内用户 | 访问稳定，性价比高 |
| OpenAI | 国际用户 | 功能强大，生态完善 |
| Anthropic | 安全场景 | 推理能力强，安全性高 |
| Mock | 测试开发 | 无需API，立即可用 |

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


## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情