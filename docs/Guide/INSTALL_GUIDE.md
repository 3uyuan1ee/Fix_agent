# 📦 AIDefectDetector 安装指南

本指南将帮助您在各种操作系统上安装AIDefectDetector，让它成为可以在任何目录下运行的强大工具。

## 🎯 安装目标

安装完成后，您将能够：

```bash
# 在任何目录下运行
python3 main.py --help
python3 main.py analyze static ./my-project
python3 main.py web

# 使用全局命令（如果安装时创建）
aidefect --help
aidefect analyze static ./my-project
aidefect-web
```

## 📋 系统要求

### 最低要求
- **Python**: 3.8 或更高版本
- **操作系统**: Linux, macOS, Windows
- **内存**: 至少 2GB RAM
- **磁盘空间**: 至少 500MB 可用空间

### 推荐配置
- **Python**: 3.9+
- **内存**: 4GB+ RAM
- **磁盘空间**: 2GB+ 可用空间
- **网络**: 稳定的互联网连接（用于LLM API调用）

## 🛠️ 安装方法

### 方法1：统一安装脚本（推荐）⭐

项目提供了跨平台的统一安装脚本，自动处理所有安装步骤。

#### Linux/macOS 安装

```bash
# 1. 克隆项目
git clone https://github.com/3uyuan1ee/Fix_agent
cd Fix_agent

# 2. 运行安装脚本
bash scripts/install_unix.sh
```

#### Windows 安装

```batch
:: 1. 克隆项目
git clone https://github.com/3uyuan1ee/Fix_agent
cd Fix_agent

:: 2. 运行安装脚本
scripts\install_windows.bat
```

**安装脚本功能特点**：
- ✅ 自动检测Python版本
- ✅ 创建并配置虚拟环境
- ✅ 安装所有依赖包
- ✅ 创建全局命令链接
- ✅ 生成基础配置文件
- ✅ 验证安装结果

### 方法2：pip开发安装

```bash
# 1. 克隆项目
git clone https://github.com/3uyuan1ee/Fix_agent
cd Fix_agent

# 2. 创建虚拟环境（推荐）
python3 -m venv aidefect_venv
source aidefect_venv/bin/activate  # Linux/macOS
# aidefect_venv\Scripts\activate   # Windows

# 3. 升级pip
pip install --upgrade pip

# 4. 安装依赖
pip install -r requirements.txt

# 5. 开发模式安装
pip install -e .
```

### 方法3：手动安装

#### 步骤1：环境准备

```bash
# 检查Python版本
python3 --version
# 或 python --version

# 确保版本 >= 3.8
```

#### 步骤2：创建虚拟环境

```bash
# Linux/macOS
python3 -m venv aidefect_venv
source aidefect_venv/bin/activate

# Windows
python -m venv aidefect_venv
aidefect_venv\Scripts\activate
```

#### 步骤3：安装依赖

```bash
# 升级pip
pip install --upgrade pip

# 安装基础依赖
pip install pyyaml loguru requests aiofiles

# 安装静态分析工具
pip install pylint flake8 bandit mccabe

# 安装Web框架
pip install flask flask-cors

# 安装LLM客户端
pip install zai-sdk

# 安装其他依赖
pip install click chardet tqdm rich python-dotenv

# 安装开发工具（可选）
pip install pytest pytest-asyncio pytest-cov black isort mypy
```

#### 步骤4：验证安装

```bash
# 测试Python导入
python3 -c "
import sys
sys.path.insert(0, 'src')
from interfaces.cli import main as cli_main
print('✅ 导入成功！')
"

# 测试主程序
python3 main.py --help
```

## 📁 详细安装步骤

### Linux/macOS 详细安装

#### 1. 系统准备

```bash
# 更新系统包管理器
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
# 或
sudo yum update -y                    # CentOS/RHEL
# 或
sudo dnf update -y                    # Fedora

# 安装基础工具
sudo apt install -y git curl wget python3 python3-pip python3-venv  # Ubuntu/Debian
# 或
sudo yum install -y git curl wget python3 python3-pip                # CentOS/RHEL
```

#### 2. 克隆项目

```bash
# 克隆仓库
git clone https://github.com/3uyuan1ee/Fix_agent
cd Fix_agent

# 检查项目结构
ls -la
```

#### 3. 运行安装脚本

```bash
# 给脚本执行权限
chmod +x scripts/install_unix.sh

# 运行安装脚本
bash scripts/install_unix.sh
```

#### 4. 验证安装

```bash
# 激活虚拟环境
source ~/.aidefect_venv/bin/activate

# 测试主程序
python3 main.py --help

# 测试静态分析
python3 main.py analyze static ./src --dry-run
```

### Windows 详细安装

#### 1. 系统准备

```batch
:: 检查Python是否安装
python --version

:: 如果没有安装，从 https://python.org 下载安装

:: 检查Git是否安装
git --version

:: 如果没有安装，从 https://git-scm.com 下载安装
```

#### 2. 克隆项目

```batch
:: 克隆仓库
git clone https://github.com/3uyuan1ee/Fix_agent
cd Fix_agent

:: 检查项目结构
dir
```

#### 3. 运行安装脚本

```batch
:: 运行安装脚本
scripts\install_windows.bat
```

#### 4. 验证安装

```batch
:: 激活虚拟环境
%USERPROFILE%\.aidefect_venv\Scripts\activate

:: 测试主程序
python main.py --help

:: 测试静态分析
python main.py analyze static .\src --dry-run
```

## 🔧 配置文件设置

### 自动生成的配置文件

安装完成后，系统会自动创建以下配置文件：

```
~/.aidefect/                    # 用户配置目录
├── config.yaml                 # 主配置文件
├── .env                        # 环境变量文件
├── logs/                       # 日志目录
└── cache/                      # 缓存目录
```

### 基础配置文件示例

**~/.aidefect/config.yaml**
```yaml
# AIDefectDetector 主配置文件

# LLM配置
llm:
  default_provider: "mock"  # 默认使用Mock模式
  max_tokens: 4000
  temperature: 0.3

# 静态分析配置
static_analysis:
  tools: ["ast", "pylint", "flake8", "bandit"]
  parallel: true
  timeout: 300

# Web界面配置
web:
  host: "127.0.0.1"
  port: 5000
  debug: false

# 日志配置
logging:
  level: "INFO"
  file: "~/.aidefect/logs/aidefect.log"
```

**~/.aidefect/.env**
```env
# API密钥配置（请在此处添加您的API密钥）

# 智谱AI（推荐国内用户）
# ZHIPU_API_KEY=your-zhipu-api-key

# OpenAI
# OPENAI_API_KEY=your-openai-api-key
# OPENAI_BASE_URL=https://api.openai.com/v1

# Anthropic
# ANTHROPIC_API_KEY=your-anthropic-api-key
# ANTHROPIC_BASE_URL=https://api.anthropic.com
```

## ✅ 安装验证

### 基础功能验证

```bash
# 1. 检查主程序
python3 main.py --help

# 2. 检查静态分析
python3 main.py analyze static . --dry-run

# 3. 检查Web界面
python3 main.py web --help

# 4. 检查配置
python3 scripts/configure_llm.py --status
```

### 完整功能验证

```bash
# 1. 静态分析测试
python3 main.py analyze static ./src --output test_static.json

# 2. 配置API密钥（如果有的话）
python3 scripts/configure_llm.py --provider mock

# 3. 深度分析测试（使用Mock模式）
python3 main.py analyze deep ./src/utils/config.py --verbose

# 4. 修复分析测试（使用Mock模式）
python3 main.py analyze fix ./src/utils/config.py --dry-run

# 5. 工作流测试（使用Mock模式）
python3 main.py analyze workflow ./src/utils/config.py --dry-run
```

### 全局命令验证（如果创建）

```bash
# 检查全局命令是否可用
aidefect --help
aidefect analyze static .
aidefect-web
```

## 🚨 常见安装问题

### 问题1：Python版本过低

**症状**：
```
Python 3.8+ is required, but you have Python 3.7
```

**解决方案**：
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.9 python3.9-venv python3.9-pip

# CentOS/RHEL
sudo yum install python39 python39-pip

# 或使用pyenv管理多版本Python
curl https://pyenv.run | bash
pyenv install 3.9.16
pyenv global 3.9.16
```

### 问题2：权限错误

**症状**：
```
Permission denied: './install_unix.sh'
```

**解决方案**：
```bash
# 添加执行权限
chmod +x scripts/install_unix.sh

# 或直接使用bash执行
bash scripts/install_unix.sh
```

### 问题3：网络连接问题

**症状**：
```
Could not fetch URL: https://pypi.org/simple/...
```

**解决方案**：
```bash
# 使用国内镜像源
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ -r requirements.txt

# 或配置永久镜像源
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 问题4：虚拟环境问题

**症状**：
```
command not found: python3
```

**解决方案**：
```bash
# 重新激活虚拟环境
source ~/.aidefect_venv/bin/activate

# 或重新创建虚拟环境
python3 -m venv ~/.aidefect_venv
source ~/.aidefect_venv/bin/activate
pip install -r requirements.txt
```

### 问题5：依赖安装失败

**症状**：
```
ERROR: Could not install packages due to EnvironmentError
```

**解决方案**：
```bash
# 升级pip和setuptools
pip install --upgrade pip setuptools wheel

# 清理pip缓存
pip cache purge

# 重新安装依赖
pip install -r requirements.txt --no-cache-dir
```

## 🔄 升级和维护

### 升级到最新版本

```bash
# 1. 备份配置
cp -r ~/.aidefect ~/.aidefect.backup

# 2. 拉取最新代码
git pull origin main

# 3. 重新安装依赖
source ~/.aidefect_venv/bin/activate
pip install -r requirements.txt --upgrade

# 4. 重新安装包
pip install -e .

# 5. 验证升级
python3 main.py --version
```

### 清理缓存

```bash
# 清理pip缓存
pip cache purge

# 清理项目缓存
rm -rf ~/.aidefect/cache/*

# 清理日志文件
rm -rf ~/.aidefect/logs/*
```

### 重新安装

```bash
# 1. 删除虚拟环境
rm -rf ~/.aidefect_venv

# 2. 删除配置文件（可选）
rm -rf ~/.aidefect

# 3. 重新运行安装脚本
bash scripts/install_unix.sh
```

## 🗑️ 卸载

### 完全卸载

```bash
# 1. 删除虚拟环境
rm -rf ~/.aidefect_venv

# 2. 删除配置目录
rm -rf ~/.aidefect

# 3. 删除全局命令（如果创建了）
sudo rm -f /usr/local/bin/aidefect*
sudo rm -f ~/.local/bin/aidefect*

# 4. 删除项目目录
cd ..
rm -rf Fix_agent
```

### 保留配置的卸载

```bash
# 只删除虚拟环境，保留配置
rm -rf ~/.aidefect_venv

# 保留配置文件 ~/.aidefect/ 用于以后重装
```

## 🎯 下一步

安装完成后，建议您：

1. **配置API密钥**：
   ```bash
   python3 scripts/configure_llm.py --quick
   ```

2. **阅读快速开始指南**：
   ```bash
   cat docs/QUICKSTART.md
   ```

3. **体验基础功能**：
   ```bash
   python3 main.py analyze static ./src
   ```

4. **配置高级功能**：
   ```bash
   python3 scripts/configure_llm.py --provider zhipu
   python3 main.py analyze deep ./src
   ```

5. **启动Web界面**：
   ```bash
   python3 main.py web
   ```

## 📞 获取帮助

如果遇到安装问题：

1. **运行诊断工具**：
   ```bash
   python3 scripts/configure_llm.py --diagnose
   ```

2. **查看详细日志**：
   ```bash
   tail -f ~/.aidefect/logs/aidefect.log
   ```

3. **检查系统环境**：
   ```bash
   python3 --version
   pip3 --version
   git --version
   ```

4. **重新安装**：
   ```bash
   bash scripts/install_unix.sh
   ```

---

**🚀 安装完成后，您就可以开始体验AIDefectDetector的强大功能了！**