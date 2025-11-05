# 📦 AIDefectDetector 安装指南

本指南将帮助你安装AIDefectDetector，让它成为可以在任何目录下运行的全局命令。

## 🎯 安装目标

安装完成后，你将能够：

```bash
# 在任何目录下运行
aidefect --help
aidefect analyze static ./my-project
aidefect-web
```

## 🛠️ 安装方法

### 方法1：自动安装（推荐）

#### Linux/macOS

```bash
# 克隆项目
git clone <repository-url>
cd AIDefectDetector

# 运行安装脚本
./install.sh
```

#### Windows

```batch
# 克隆项目
git clone <repository-url>
cd AIDefectDetector

# 运行安装脚本
install.bat
```

### 方法2：pip安装

```bash
# 克隆项目
git clone <repository-url>
cd AIDefectDetector

# 开发模式安装
pip install -e .

# 或者生产模式安装
pip install .
```

### 方法3：手动安装

#### 步骤1：准备环境

```bash
# 确保Python 3.8+已安装
python3 --version

# 创建虚拟环境（可选但推荐）
python3 -m venv aidefect_env
source aidefect_env/bin/activate  # Linux/macOS
# 或
aidefect_env\Scripts\activate     # Windows
```

#### 步骤2：安装依赖

```bash
pip install -r requirements.txt
```

#### 步骤3：安装包

```bash
# 开发模式安装（推荐开发者使用）
pip install -e .

# 生产模式安装
pip install .
```

#### 步骤4：创建全局链接（Linux/macOS）

```bash
# 创建符号链接
sudo ln -s $(pwd)/aidefect /usr/local/bin/aidefect
sudo chmod +x /usr/local/bin/aidefect
```

#### 步骤4：创建全局脚本（Windows）

```batch
# 创建批处理文件
echo @echo off > %USERPROFILE%\AppData\Local\Microsoft\WindowsApps\aidefect.bat
echo "<path-to-aidefect>\aidefect" %%* >> %USERPROFILE%\AppData\Local\Microsoft\WindowsApps\aidefect.bat
```

## ✅ 验证安装

### 基础验证

```bash
# 检查命令是否可用
aidefect --help

# 预期输出：
# AIDefectDetector - 基于AI Agent的软件项目缺陷自主检测与修复系统
# ======================================================================
#
# 使用方法:
#     aidefect [选项]
#
# 选项:
#     web             启动Web界面
#     help, -h        显示此帮助信息
#
# 示例:
#     aidefect              # 启动CLI模式
#     aidefect web          # 启动Web界面
```

### 功能验证

```bash
# 测试CLI模式
aidefect

# 测试Web模式（如果安装了Flask）
aidefect-web

# 在任意目录测试
cd /tmp
aidefect --help
```

## 🔧 配置

### 配置文件位置

- **Linux/macOS**: `~/.aidefect/config.yaml`
- **Windows**: `%USERPROFILE%\.aidefect\config.yaml`

### API密钥配置

```yaml
# ~/.aidefect/config.yaml
llm:
  default_provider: "openai"  # 或 "anthropic", "zhipu"

  openai:
    api_key: "your-openai-api-key"
    model: "gpt-4"

  anthropic:
    api_key: "your-anthropic-api-key"
    model: "claude-3-sonnet-20240229"

  zhipu:
    api_key: "your-zhipu-api-key"
    model: "glm-4"
```

## 🎯 使用方法

### CLI模式

```bash
# 显示帮助
aidefect --help

# 静态分析
aidefect analyze static ./your-project

# 深度分析（需要API密钥）
aidefect analyze deep ./your-project

# 修复分析（需要API密钥）
aidefect analyze fix ./your-project
```

### Web界面

```bash
# 启动Web服务
aidefect-web

# 访问
http://localhost:5000
```

## 🛠️ 故障排除

### 问题1：命令找不到

**症状**：
```bash
aidefect --help
# bash: aidefect: command not found
```

**解决方案**：

**Linux/macOS**：
```bash
# 检查PATH
echo $PATH | grep -o "[^:]*bin[^:]*"

# 手动添加到PATH（临时）
export PATH=$PATH:/usr/local/bin

# 永久添加到PATH
echo 'export PATH=$PATH:/usr/local/bin' >> ~/.bashrc
source ~/.bashrc
```

**Windows**：
```batch
# 检查PATH
echo %PATH%

# 手动添加到PATH
set PATH=%PATH%;C:\Python\Scripts
```

### 问题2：权限错误

**症状**：
```bash
./aidefect --help
# Permission denied
```

**解决方案**：
```bash
# 添加执行权限
chmod +x aidefect

# 或使用Python运行
python3 aidefect --help
```

### 问题3：导入错误

**症状**：
```bash
aidefect --help
# ImportError: No module named 'src.interfaces.cli'
```

**解决方案**：

1. **确保在项目目录中**：
```bash
cd /path/to/AIDefectDetector
./aidefect --help
```

2. **重新安装**：
```bash
pip uninstall aidefect
pip install -e .
```

3. **检查Python路径**：
```bash
python3 -c "import sys; print('\n'.join(sys.path))"
```

### 问题4：虚拟环境问题

**症状**：
```bash
aidefect --help
# python: command not found
```

**解决方案**：

1. **重新激活虚拟环境**：
```bash
source ~/.aidefect_venv/bin/activate
```

2. **或使用系统Python**：
```bash
# 编辑 aidefect 脚本，将 python3 改为 /usr/bin/python3
```

### 问题5：Flask依赖问题

**症状**：
```bash
aidefect-web
# ImportError: No module named 'flask'
```

**解决方案**：
```bash
# 安装Flask
pip install flask

# 或安装完整依赖
pip install -r requirements.txt
```

## 🔄 卸载

### 方法1：pip卸载

```bash
pip uninstall aidefect
```

### 方法2：手动卸载

**Linux/macOS**：
```bash
# 删除全局链接
sudo rm /usr/local/bin/aidefect
sudo rm /usr/local/bin/aidefect-web

# 删除配置目录
rm -rf ~/.aidefect
```

**Windows**：
```batch
# 删除全局脚本
del %USERPROFILE%\AppData\Local\Microsoft\WindowsApps\aidefect.bat
del %USERPROFILE%\AppData\Local\Microsoft\WindowsApps\aidefect-web.bat

# 删除配置目录
rmdir /s %USERPROFILE%\.aidefect
```

### 卸载虚拟环境（可选）

```bash
# 删除虚拟环境
rm -rf ~/.aidefect_venv
```

## 🎉 安装成功！

安装完成后，你现在可以：

1. **在任何目录下使用** `aidefect` 命令
2. **查看帮助** `aidefect --help`
3. **启动Web界面** `aidefect-web`
4. **分析代码** `aidefect analyze static ./my-project`

## 📚 更多资源

- [快速开始指南](../QUICKSTART.md) - 5分钟上手
- [完整文档](../README.md) - 详细使用说明
- [演示指南](../../Dev/DEMO_GUIDE.md) - 功能演示
- [项目概览](../OVERVIEW.md) - 架构说明

---

**🚀 享受智能代码分析的乐趣！**