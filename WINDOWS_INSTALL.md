# Windows 安装指南

## 🚀 快速安装

### 方式1: pip安装 (推荐)
```cmd
pip install Fix_agent
```

### 方式2: 便携版下载
1. 访问 [Releases页面](https://github.com/3uyuan1ee/Fix_agent/releases)
2. 下载 `Fix_Agent_0.1.1_Portable.zip`
3. 解压到任意目录
4. 双击 `Fix_Agent.bat` 启动

### 方式3: 安装包
1. 下载 `Fix_Agent_0.1.1_Setup.exe`
2. 双击运行安装程序
3. 按照向导完成安装
4. 从开始菜单启动

## 📋 系统要求

### 必需软件
- **Python 3.11+** ([下载地址](https://www.python.org/downloads/))
  - 安装时勾选 "Add to PATH"
  - 验证安装: `python --version`

### 可选软件
- **Node.js 16+** ([下载地址](https://nodejs.org/))
  - 用于JavaScript项目分析
- **Git** ([下载地址](https://git-scm.com/))
  - 用于版本控制项目分析

## ⚙️ 配置

### 1. 设置API密钥
创建 `.env` 文件并配置：
```env
# OpenAI API密钥 (推荐)
OPENAI_API_KEY=your_openai_key_here

# Anthropic API密钥
ANTHROPIC_API_KEY=your_anthropic_key_here

# Tavily搜索API密钥 (可选)
TAVILY_API_KEY=your_tavily_key_here
```

### 2. 设置编辑器 (可选)
```cmd
# 使用记事本
set EDITOR=notepad

# 使用VS Code
set EDITOR=code

# 使用Notepad++
set EDITOR=notepad++
```

## 🎯 Windows特定功能

### PowerShell支持
Fix Agent完全支持PowerShell命令：
```cmd
# 启动Fix Agent
fix-agent

# 使用PowerShell命令
! pwsh Get-Process
! powershell Get-ChildItem

# 常规cmd命令仍然有效
! dir
! echo "Hello Windows"
```

### 系统信息查看
```cmd
# 查看系统信息
/sys

# 查看Windows服务
/services list
/services search "mysql"
/services status "nginx"
```

### 服务管理 (管理员权限)
```cmd
# 启动服务
/services start "mysql"

# 停止服务
/services stop "nginx"

# 重启服务
/services restart "apache"
```

### WSL支持
如果在WSL环境中运行，Fix Agent会自动检测并提供：
- Windows文件系统访问 (`/mnt/c/`)
- Windows工具集成
- 跨平台路径处理

## 🔧 故障排除

### 常见问题

#### 1. "python不是内部或外部命令"
**解决方案**:
- 重新安装Python，勾选"Add to PATH"
- 或手动添加Python到PATH环境变量

#### 2. "PowerShell命令不可用"
**解决方案**:
- Windows 10/11自带PowerShell
- 如需PowerShell 7，安装[PowerShell 7](https://github.com/PowerShell/PowerShell)

#### 3. 服务管理权限错误
**解决方案**:
- 以管理员身份运行Fix Agent
- 或使用 `services.msc` 手动管理服务

#### 4. 编码问题
**解决方案**:
- 设置控制台编码: `chcp 65001`
- 使用Windows Terminal替代cmd

### 性能优化

#### 1. 使用虚拟环境
```cmd
# 创建虚拟环境
python -m venv fix-agent-env

# 激活虚拟环境
fix-agent-env\Scripts\activate

# 安装Fix Agent
pip install Fix_agent
```

#### 2. 配置Windows Terminal
推荐安装Windows Terminal以获得更好的体验：
- 多标签页支持
- 更好的Unicode支持
- 自定义外观

## 🎮 使用示例

### 基本操作
```cmd
# 启动Fix Agent
fix-agent

# 查看帮助
/help

# 清屏
/clear

# 查看Token使用量
/tokens

# 配置环境变量
/config
```

### 项目分析
```cmd
# 分析Python项目
请分析这个Python项目的代码质量 C:\Users\username\my-python-project

# 分析JavaScript项目
检查这个Node.js项目的潜在问题 C:\Users\username\my-nodejs-app

# 分析跨平台项目
分析这个全栈项目的代码结构 C:\Users\username\web-app
```

### 系统管理
```cmd
# 查看系统信息
/sys

# 查看运行进程
! pwsh Get-Process | Where-Object {$_.CPU -gt 10}

# 查看磁盘空间
! wmic logicaldisk get size,freespace,caption

# 管理服务
/services list
/services search "sql"
```

## 📁 文件位置

### 安装文件位置
- **便携版**: 解压目录
- **安装版**: `C:\Program Files\Fix Agent\`

### 配置文件
- **环境配置**: `\.env`
- **用户配置**: `%APPDATA%\Fix Agent\`
- **日志文件**: `%APPDATA%\Fix Agent\logs\`

### 临时文件
- **缓存**: `%TEMP%\Fix Agent\`
- **会话数据**: `%APPDATA%\Fix Agent\sessions\`

## 🔄 更新

### 通过pip更新
```cmd
pip install --upgrade Fix_agent
```

### 手动更新
1. 下载新版本
2. 卸载旧版本: `pip uninstall Fix_agent`
3. 安装新版本: `pip install Fix_agent_x.x.x-py3-none-any.whl`

## 🤝 技术支持

### 获取帮助
- **GitHub Issues**: [报告问题](https://github.com/3uyuan1ee/Fix_agent/issues)
- **文档**: [在线文档](https://github.com/3uyuan1ee/Fix_agent#readme)

### 反馈渠道
- **功能建议**: 在GitHub Issues中标记为"enhancement"
- **Bug报告**: 提供系统信息、错误信息和复现步骤

---

**最后更新**: 2025年11月12日
**版本**: Fix Agent v0.1.1