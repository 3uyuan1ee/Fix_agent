#!/usr/bin/env python3
"""
创建Windows发布包（便携版和安装包）
"""

import os
import sys
import subprocess
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

def get_version():
    """获取项目版本号."""
    try:
        with open("pyproject.toml", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith('version = '):
                    return line.split('=')[1].strip().strip('"\'')
    except Exception:
        pass
    return "0.1.1"

def create_portable_package():
    """创建便携版包."""
    print("📦 创建Windows便携版包...")

    version = get_version()
    package_name = f"Fix_Agent_{version}_Portable_Windows"
    package_dir = Path("dist") / package_name

    # 创建目录结构
    package_dir.mkdir(parents=True, exist_ok=True)

    print(f"  📁 创建目录: {package_dir}")

    # 复制Python包
    print("  📋 复制Python包...")
    dist_files = list(Path("dist").glob("*.whl"))
    dist_files.extend(Path("dist").glob("*.tar.gz"))

    for wheel_file in dist_files:
        if wheel_file.name.startswith("Fix_agent"):
            shutil.copy2(wheel_file, package_dir)
            print(f"    ✅ 复制 {wheel_file.name}")

    # 复制Windows启动脚本
    print("  📄 复制Windows启动脚本...")
    if Path("windows").exists():
        windows_files = list(Path("windows").glob("*"))
        for file in windows_files:
            if file.is_file():
                shutil.copy2(file, package_dir)
                print(f"    ✅ 复制 {file.name}")

    # 创建启动脚本（如果windows目录不存在）
    else:
        create_launch_script(package_dir)

    # 复制文档
    print("  📚 复制文档...")
    docs_to_copy = [
        "README.md",
        "LICENSE",
        "WINDOWS.md",
        "CHANGELOG.md"
    ]

    for doc in docs_to_copy:
        if Path(doc).exists():
            shutil.copy2(doc, package_dir)
            print(f"    ✅ 复制 {doc}")

    # 创建安装脚本
    create_install_script(package_dir, version)

    # 创建zip包
    print("  🗜️  创建ZIP包...")
    zip_path = Path("dist") / f"{package_name}.zip"

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in package_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(package_dir.parent)
                zipf.write(file_path, arcname)

    print(f"  ✅ 便携版包已创建: {zip_path}")
    return str(zip_path)


def create_launch_script(package_dir):
    """创建启动脚本."""
    print("    📝 创建启动脚本...")

    # 创建安装脚本
    install_script = """@echo off
title Fix Agent 安装
echo Fix Agent 便携版安装程序
echo ==========================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python
    echo 请先安装Python 3.11+并添加到PATH
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python已安装，开始安装Fix Agent...
echo.

REM 安装依赖
echo 安装依赖包...
python -m pip install --upgrade pip
python -m pip install Fix_agent-*.whl

if errorlevel 1 (
    echo.
    echo 错误: 安装失败
    pause
    exit /b 1
)

echo.
echo ✅ Fix Agent安装成功！
echo.
echo 使用方法:
echo   fix-agent          # 启动Fix Agent
echo   fix-agent --help   # 查看帮助
echo.
echo 请配置API密钥:
echo   1. 创建 .env 文件
echo   2. 添加: OPENAI_API_KEY=your_key_here
echo   3. 或使用 /config 命令配置
echo.
pause
"""

    with open(package_dir / "install.bat", "w", encoding="utf-8") as f:
        f.write(install_script)

    # 创建启动脚本
    run_script = """@echo off
title Fix Agent
echo 启动 Fix Agent...
echo.

python -m Fix_agent %*

if errorlevel 1 (
    echo.
    echo Fix Agent 退出时出现错误
    pause
)
"""

    with open(package_dir / "Fix_Agent.bat", "w", encoding="utf-8") as f:
        f.write(run_script)


def create_install_script(package_dir, version):
    """创建安装说明和脚本."""
    install_guide = f"""# Fix Agent {version} - Windows便携版安装说明

## 安装步骤

1. **检查Python环境**
   ```cmd
   python --version
   ```
   需要Python 3.11+版本

2. **运行安装脚本**
   ```cmd
   install.bat
   ```

3. **配置API密钥**
   创建 `.env` 文件并添加:
   ```env
   OPENAI_API_KEY=your_openai_key_here
   # 或
   ANTHROPIC_API_KEY=your_anthropic_key_here
   ```

4. **启动Fix Agent**
   ```cmd
   Fix_Agent.bat
   ```

## 使用方法

### 基本命令
```cmd
# 启动交互式会话
fix-agent

# 查看帮助
fix-agent --help

# 查看系统信息
fix-agent
> /sys

# 管理Windows服务
fix-agent
> /services list
```

### Windows特定功能
- PowerShell命令支持: `! pwsh Get-Process`
- Windows服务管理: `/services start mysql`
- WSL环境检测
- 跨平台路径处理

## 故障排除

1. **Python未找到**
   - 安装Python 3.11+: https://www.python.org/downloads/
   - 安装时勾选"Add to PATH"

2. **依赖安装失败**
   ```cmd
   python -m pip install --upgrade pip
   python -m pip install Fix_agent-*.whl --force-reinstall
   ```

3. **权限错误**
   - 以管理员身份运行命令提示符
   - 或使用用户级安装: `python -m pip install --user`

## 更多信息

- 完整文档: https://github.com/3uyuan1ee/Fix_agent
- 问题报告: https://github.com/3uyuan1ee/Fix_agent/issues
- 版本: {version}
- 构建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    with open(package_dir / "INSTALL.md", "w", encoding="utf-8") as f:
        f.write(install_guide)


def create_installer_package():
    """尝试创建安装包（如果有NSIS）."""
    print("\n🏗️  尝试创建Windows安装包...")

    # 检查NSIS
    nsis_path = shutil.which("makensis")
    if not nsis_path:
        print("  ⚠️  NSIS未找到，跳过安装包创建")
        print("  💡 安装NSIS: https://nsis.sourceforge.io/")
        return False

    print("  ✅ 找到NSIS，创建安装包...")

    version = get_version()

    # NSIS脚本
    nsis_script = f"""
; Fix Agent Windows安装程序脚本

!define APPNAME "Fix Agent"
!define VERSION "{version}"
!define PUBLISHER "3uyuan1ee"
!define URL "https://github.com/3uyuan1ee/Fix_agent"

!include "MUI2.nsh"

; 基本设置
Name "${{APPNAME}}"
OutFile "dist\\Fix_Agent_${{VERSION}}_Setup.exe"
InstallDir "$PROGRAMFILES\\${{APPNAME}}"
InstallDirRegKey HKLM "Software\\${{APPNAME}}" "InstallPath"
RequestExecutionLevel admin

; 版本信息
VIProductVersion "${{VERSION}}.0"
VIAddVersionKey "ProductName" "${{APPNAME}}"
VIAddVersionKey "CompanyName" "${{PUBLISHER}}"
VIAddVersionKey "LegalCopyright" "MIT License"
VIAddVersionKey "FileDescription" "AI代码缺陷修复工具"
VIAddVersionKey "FileVersion" "${{VERSION}}"

; 界面设置
!define MUI_ABORTWARNING
!define MUI_ICON "docs\\icon.ico"
!define MUI_UNICON "docs\\icon.ico"

; 安装页面
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; 卸载页面
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; 语言
!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "English"

; 安装节
Section "MainSection" SEC01
    SetOutPath "$INSTDIR"

    ; 安装Python包
    File /nonfatal "dist\\Fix_agent-*.whl"

    ; 安装文档
    File "README.md"
    File "LICENSE"
    File "WINDOWS.md"

    ; 创建启动脚本
    CreateShortCut "$SMPROGRAMS\\${{APPNAME}}\\${{APPNAME}}.lnk" "$INSTDIR\\Fix_Agent.bat"
    CreateShortCut "$SMPROGRAMS\\${{APPNAME}}\\Uninstall.lnk" "$INSTDIR\\Uninstall.exe"
    CreateShortCut "$DESKTOP\\${{APPNAME}}.lnk" "$INSTDIR\\Fix_Agent.bat"

    ; 写入注册表
    WriteRegStr HKLM "Software\\${{APPNAME}}" "InstallPath" "$INSTDIR"
    WriteRegStr HKLM "Software\\${{APPNAME}}" "Version" "${{VERSION}}"

    ; 卸载信息
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "DisplayName" "${{APPNAME}}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "UninstallString" "$INSTDIR\\Uninstall.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "DisplayVersion" "${{VERSION}}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "Publisher" "${{PUBLISHER}}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "URLInfoAbout" "${{URL}}"
SectionEnd

; 卸载节
Section "Uninstall"
    Delete "$INSTDIR\\Uninstall.exe"
    Delete "$INSTDIR\\*.*"
    RMDir /r "$INSTDIR"

    Delete "$SMPROGRAMS\\${{APPNAME}}\\*.*"
    RMDir "$SMPROGRAMS\\${{APPNAME}}"
    Delete "$DESKTOP\\${{APPNAME}}.lnk"

    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}"
    DeleteRegKey HKLM "Software\\${{APPNAME}}"
SectionEnd
"""

    # 保存NSIS脚本
    nsis_file = Path("installer.nsi")
    with open(nsis_file, "w", encoding="utf-8") as f:
        f.write(nsis_script)

    # 编译安装包
    try:
        result = subprocess.run([nsis_path, str(nsis_file)], check=True, capture_output=True)
        print("  ✅ NSIS安装包已创建")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ NSIS编译失败: {e}")
        return False


def main():
    """主函数."""
    print("🚀 Fix Agent Windows包构建工具")
    print("=" * 50)

    # 检查版本
    version = get_version()
    print(f"📦 版本: {version}")

    # 创建便携版包
    portable_path = create_portable_package()

    # 尝试创建安装包
    installer_success = create_installer_package()

    print("\n✅ 构建完成!")
    print("\n📂 生成的文件:")
    print(f"  - {portable_path}")

    if installer_success:
        print("  - dist/Fix_Agent_{version}_Setup.exe")

    print("\n🚀 发布步骤:")
    print("1. 测试便携版包")
    print("2. 测试安装包（如果有）")
    print("3. 上传到GitHub Releases")
    print("4. 发布到PyPI")
    print("\nPyPI发布命令:")
    print("  python -m build")
    print("  twine upload dist/*")


if __name__ == "__main__":
    main()