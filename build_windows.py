#!/usr/bin/env python3
"""
Windows安装包构建脚本
使用NSIS或Inno Setup创建Windows安装包
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_requirements():
    """检查构建要求."""
    print("🔍 检查构建环境...")

    # 检查Python版本
    if sys.version_info < (3, 11):
        print("❌ 需要Python 3.11+")
        return False

    # 检查必要的工具
    tools = {
        "makensis": "NSIS安装包工具",
        "iscc": "Inno Setup编译器"
    }

    available_tools = []
    for tool, description in tools.items():
        if shutil.which(tool):
            available_tools.append((tool, description))
            print(f"✅ {description} 已安装")
        else:
            print(f"⚠️  {description} 未找到")

    if not available_tools:
        print("❌ 未找到安装包构建工具")
        print("请安装NSIS或Inno Setup:")
        print("- NSIS: https://nsis.sourceforge.io/")
        print("- Inno Setup: https://jrsoftware.org/isinfo.php")
        return False

    return True, available_tools


def create_portable_package():
    """创建便携版包."""
    print("\n📦 创建便携版包...")

    # 创建临时目录
    build_dir = Path("dist/windows_portable")
    build_dir.mkdir(parents=True, exist_ok=True)

    # 复制Python包
    print("📋 复制Python包...")
    subprocess.run([
        sys.executable, "-m", "build", "--wheel", "--outdir", str(build_dir)
    ], check=True)

    # 创建启动脚本
    start_script = build_dir / "Fix_Agent.bat"
    with open(start_script, 'w') as f:
        f.write("""@echo off
title Fix Agent - AI代码缺陷修复工具
echo Starting Fix Agent...
echo.
python -m Fix_agent
pause
""")

    # 创建README
    readme = build_dir / "README_Windows.txt"
    with open(readme, 'w', encoding='utf-8') as f:
        f.write("""Fix Agent - Windows便携版

安装要求:
- Python 3.11+ 已安装并添加到PATH
- 建议使用虚拟环境

使用方法:
1. 双击 Fix_Agent.bat 启动
2. 或在命令行运行: python -m Fix_agent

配置:
1. 创建 .env 文件配置API密钥
2. 使用 /config 命令配置环境变量

故障排除:
- 确保Python在PATH中
- 检查API密钥配置
- 查看错误日志获取详细信息

更多信息: https://github.com/3uyuan1ee/Fix_agent
""")

    print(f"✅ 便携版已创建: {build_dir}")
    return True


def create_nsis_installer():
    """使用NSIS创建安装包."""
    print("\n🏗️  使用NSIS创建安装包...")

    nsis_script = """
; Fix Agent NSIS安装脚本

!define APPNAME "Fix Agent"
!define VERSION "0.1.1"
!define PUBLISHER "3uyuan1ee"
!define URL "https://github.com/3uyuan1ee/Fix_agent"
!define DESCRIPTION "AI代码缺陷修复和分析工具"

; 包含现代UI
!include "MUI2.nsh"

; 基本设置
Name "${APPNAME}"
OutFile "Fix_Agent_${VERSION}_Setup.exe"
InstallDir "$PROGRAMFILES\\${APPNAME}"
InstallDirRegKey HKLM "Software\\${APPNAME}" "InstallPath"
RequestExecutionLevel admin

; 版本信息
VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "${APPNAME}"
VIAddVersionKey "CompanyName" "${PUBLISHER}"
VIAddVersionKey "LegalCopyright" "MIT License"
VIAddVersionKey "FileDescription" "${DESCRIPTION}"
VIAddVersionKey "FileVersion" "${VERSION}"

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

    ; 文件安装
    File /r "dist\\*"
    File "README.md"
    File "LICENSE"

    ; 创建开始菜单快捷方式
    CreateDirectory "$SMPROGRAMS\\${APPNAME}"
    CreateShortCut "$SMPROGRAMS\\${APPNAME}\\${APPNAME}.lnk" "$INSTDIR\\python.exe" "-m Fix_agent" "$INSTDIR\\Fix_agent.ico" 0 "" ""
    CreateShortCut "$SMPROGRAMS\\${APPNAME}\\Uninstall.lnk" "$INSTDIR\\Uninstall.exe"

    ; 创建桌面快捷方式
    CreateShortCut "$DESKTOP\\${APPNAME}.lnk" "$INSTDIR\\python.exe" "-m Fix_agent" "$INSTDIR\\Fix_agent.ico" 0 "" ""

    ; 注册表
    WriteRegStr HKLM "Software\\${APPNAME}" "InstallPath" "$INSTDIR"
    WriteRegStr HKLM "Software\\${APPNAME}" "Version" "${VERSION}"

    ; 卸载信息
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "DisplayName" "${APPNAME}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "UninstallString" "$INSTDIR\\Uninstall.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "DisplayVersion" "${VERSION}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "Publisher" "${PUBLISHER}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "URLInfoAbout" "${URL}"
SectionEnd

; 卸载节
Section "Uninstall"
    Delete "$INSTDIR\\Uninstall.exe"
    Delete "$INSTDIR\\*.*"
    RMDir /r "$INSTDIR"

    Delete "$SMPROGRAMS\\${APPNAME}\\*.*"
    RMDir "$SMPROGRAMS\\${APPNAME}"
    Delete "$DESKTOP\\${APPNAME}.lnk"

    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}"
    DeleteRegKey HKLM "Software\\${APPNAME}"
SectionEnd
"""

    # 保存NSIS脚本
    nsis_file = Path("installer.nsi")
    with open(nsis_file, 'w', encoding='utf-8') as f:
        f.write(nsis_script)

    # 编译NSIS脚本
    try:
        subprocess.run(["makensis", str(nsis_file)], check=True)
        print("✅ NSIS安装包已创建: Fix_Agent_0.1.1_Setup.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ NSIS编译失败: {e}")
        return False


def create_inno_setup():
    """使用Inno Setup创建安装包."""
    print("\n🏗️  使用Inno Setup创建安装包...")

    inno_script = """
; Fix Agent Inno Setup安装脚本

[Setup]
AppName=Fix Agent
AppVersion=0.1.1
AppPublisher=3uyuan1ee
AppPublisherURL=https://github.com/3uyuan1ee/Fix_agent
AppSupportURL=https://github.com/3uyuan1ee/Fix_agent/issues
AppUpdatesURL=https://github.com/3uyuan1ee/Fix_agent
DefaultDirName={pf}\\Fix Agent
DefaultGroupName=Fix Agent
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=dist
OutputBaseFilename=Fix_Agent_0.1.1_Setup
SetupIconFile=docs\\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\\ChineseSimp.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\\Fix Agent"; Filename: "{app}\\python.exe"; Parameters: "-m Fix_agent"; WorkingDir: "{app}"; IconFilename: "{app}\\Fix_agent.ico"
Name: "{group}\\{cm:UninstallProgram,Fix Agent}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\\Fix Agent"; Filename: "{app}\\python.exe"; Parameters: "-m Fix_agent"; WorkingDir: "{app}"; Tasks: desktopicon; IconFilename: "{app}\\Fix_agent.ico"

[Run]
Filename: "{app}\\python.exe"; Parameters: "--version"; Description: "{cm:LaunchProgram,Fix Agent}"; Flags: shellexec postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
"""

    # 保存Inno Setup脚本
    inno_file = Path("installer.iss")
    with open(inno_file, 'w', encoding='utf-8') as f:
        f.write(inno_script)

    # 编译Inno Setup脚本
    try:
        subprocess.run(["iscc", str(inno_file)], check=True)
        print("✅ Inno Setup安装包已创建: Fix_Agent_0.1.1_Setup.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Inno Setup编译失败: {e}")
        return False


def main():
    """主函数."""
    print("🚀 Fix Agent Windows安装包构建工具")
    print("=" * 50)

    # 检查构建要求
    result = check_requirements()
    if not result:
        sys.exit(1)

    available_tools = result[1] if isinstance(result, tuple) else []

    # 构建Python包
    print("\n📦 构建Python包...")
    subprocess.run([sys.executable, "-m", "build"], check=True)

    # 创建便携版
    create_portable_package()

    # 创建安装包
    for tool, description in available_tools:
        if tool == "makensis":
            create_nsis_installer()
        elif tool == "iscc":
            create_inno_setup()

    print("\n✅ 构建完成!")
    print("\n📂 生成的文件:")
    print("  - dist/windows_portable/ (便携版)")
    print("  - dist/Fix_Agent_0.1.1_Setup.exe (安装包)")


if __name__ == "__main__":
    main()