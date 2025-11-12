#!/usr/bin/env python3
"""
跨平台构建脚本 - 为PyPI发布准备所有平台的包
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_environment():
    """检查构建环境."""
    print("🔍 检查构建环境...")

    # 检查Python版本
    if sys.version_info < (3, 11):
        print("❌ 需要Python 3.11+")
        return False

    print(f"✅ Python {sys.version}")

    # 检查构建工具
    required_tools = ["build", "twine"]
    missing_tools = []

    for tool in required_tools:
        found = False
        try:
            # 尝试导入工具
            if tool == "build":
                import build
                print(f"✅ {tool} 已安装")
                found = True
            elif tool == "twine":
                import twine
                print(f"✅ {tool} 已安装")
                found = True
        except ImportError:
            pass

        # 如果导入失败，尝试检查命令
        if not found:
            try:
                result = subprocess.run([tool, "--version"],
                                      capture_output=True, check=True, timeout=5)
                print(f"✅ {tool} 已安装")
                found = True
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                pass

        if not found and tool == "build":
            try:
                result = subprocess.run([sys.executable, "-c", "import build; print('build module available')"],
                                      capture_output=True, check=True, timeout=5)
                print(f"✅ {tool} 已安装 (作为Python模块)")
                found = True
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                pass

        if not found:
            missing_tools.append(tool)
            print(f"❌ {tool} 未找到")

    if missing_tools:
        print(f"\n请安装缺失的工具:")
        print(f"pip install {' '.join(missing_tools)}")
        return False

    return True


def clean_build():
    """清理构建目录."""
    print("\n🧹 清理构建目录...")

    dirs_to_clean = ["build", "dist", "*.egg-info"]

    for pattern in dirs_to_clean:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
                print(f"  删除目录: {path}")
            else:
                path.unlink()
                print(f"  删除文件: {path}")


def build_package():
    """构建Python包."""
    print("\n📦 构建Python包...")

    try:
        # 使用build模块构建
        result = subprocess.run([
            sys.executable, "-m", "build"
        ], check=True, capture_output=True, text=True)

        print("✅ 包构建成功")
        print(f"输出: {result.stdout}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ 构建失败: {e}")
        print(f"错误: {e.stderr}")
        return False


def create_windows_artifacts():
    """创建Windows特定的构建产物."""
    print("\n🪟 创建Windows构建产物...")

    import platform

    if platform.system() != "Windows":
        print("⚠️  非Windows系统，跳过Windows特定构建")
        return True

    # 创建Windows启动脚本
    create_windows_launchers()

    # 创建Windows安装说明
    create_windows_readme()

    return True


def create_windows_launchers():
    """创建Windows启动脚本."""
    print("  📄 创建Windows启动脚本...")

    launchers_dir = Path("windows")
    launchers_dir.mkdir(exist_ok=True)

    # 创建Fix_Agent.bat
    bat_content = '''@echo off
title Fix Agent - AI代码缺陷修复工具
echo Starting Fix Agent...
echo.

REM 检查Python是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found in PATH
    echo Please install Python 3.11+ and add it to PATH
    pause
    exit /b 1
)

REM 启动Fix Agent
python -m Fix_agent %*

if errorlevel 1 (
    echo.
    echo Fix Agent exited with an error
    pause
)
'''

    with open(launchers_dir / "Fix_Agent.bat", "w", encoding="utf-8") as f:
        f.write(bat_content)

    # 创建Fix_Agent.ps1 (PowerShell)
    ps_content = '''# Fix Agent PowerShell启动脚本
param(
    [string[]]$Args
)

# 检查Python版本
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: Python not found" -ForegroundColor Red
    Write-Host "Please install Python 3.11+ and add it to PATH" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# 启动Fix Agent
Write-Host "Starting Fix Agent..." -ForegroundColor Cyan
Write-Host ""

try {
    python -m Fix_agent $Args
} catch {
    Write-Host "Fix Agent exited with an error" -ForegroundColor Red
    if ($Host.Name -eq "ConsoleHost") {
        Read-Host "Press Enter to exit"
    }
}
'''

    with open(launchers_dir / "Fix_Agent.ps1", "w", encoding="utf-8") as f:
        f.write(ps_content)

    print("    ✅ 启动脚本已创建")


def create_windows_readme():
    """创建Windows特定的README."""
    print("  📄 创建Windows安装说明...")

    readme_content = '''# Fix Agent - Windows安装指南

## 快速开始

### 1. 使用pip安装 (推荐)
```cmd
pip install Fix_agent
```

### 2. 使用启动脚本
下载Windows发布包后：
- 双击 `Fix_Agent.bat` 启动
- 或在PowerShell中运行: .\\Fix_Agent.ps1

## 系统要求
- Python 3.11+
- Windows 10/11 (推荐)

## 配置API密钥
1. 创建 `.env` 文件
2. 添加您的API密钥:
```env
OPENAI_API_KEY=your_api_key_here
ANTHROPIC_API_KEY=your_api_key_here
```

## 使用方法
```cmd
# 启动交互式会话
fix-agent

# 查看帮助
fix-agent --help

# 查看系统信息 (Windows特定功能)
fix-agent
> /sys

# 管理Windows服务
fix-agent
> /services list
```

## 更多信息
- 完整文档: https://github.com/3uyuan1ee/Fix_agent
- 问题报告: https://github.com/3uyuan1ee/Fix_agent/issues
'''

    with open("WINDOWS.md", "w", encoding="utf-8") as f:
        f.write(readme_content)

    print("    ✅ Windows安装说明已创建")


def check_package():
    """检查包的有效性."""
    print("\n🔍 检查包的有效性...")

    # 查找构建的包
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("❌ dist目录不存在")
        return False

    packages = list(dist_dir.glob("*"))
    if not packages:
        print("❌ 没有找到构建的包")
        return False

    print(f"📦 找到 {len(packages)} 个包:")
    for pkg in packages:
        print(f"  - {pkg.name}")

    # 使用twine检查
    try:
        print("\n🔍 使用twine检查包...")
        subprocess.run([
            "twine", "check", "dist/*"
        ], check=True)
        print("✅ 包检查通过")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ 包检查失败: {e}")
        return False


def main():
    """主构建流程."""
    print("🚀 Fix Agent PyPI构建工具")
    print("=" * 50)

    # 检查环境
    if not check_environment():
        sys.exit(1)

    # 清理构建目录
    clean_build()

    # 构建包
    if not build_package():
        sys.exit(1)

    # 创建Windows特定文件
    create_windows_artifacts()

    # 检查包
    if not check_package():
        sys.exit(1)

    print("\n✅ 构建完成!")
    print("\n📂 构建产物:")
    print("  - dist/ (PyPI包)")
    print("  - windows/ (Windows启动脚本)")
    print("  - WINDOWS.md (Windows安装指南)")

    print("\n🚀 发布到PyPI:")
    print("  # 测试PyPI")
    print("  twine upload --repository testpypi dist/*")
    print("")
    print("  # 正式PyPI")
    print("  twine upload dist/*")


if __name__ == "__main__":
    main()