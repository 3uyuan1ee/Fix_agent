@echo off
:: AIDefectDetector Windows 全局安装脚本

setlocal enabledelayedexpansion

echo.
echo 🚀 AIDefectDetector 全局安装脚本
echo ====================================
echo.

:: 检查Python版本
echo [INFO] 检查Python环境...

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 未安装，请先安装Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [SUCCESS] Python版本检查通过: %PYTHON_VERSION%

:: 检查pip
echo [INFO] 检查pip...

pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip 未安装，请确保pip已正确安装
    pause
    exit /b 1
)

echo [SUCCESS] pip检查通过

:: 创建虚拟环境
echo [INFO] 创建虚拟环境...

set VENV_DIR=%USERPROFILE%\.aidefect_venv

if exist "%VENV_DIR%" (
    echo [WARNING] 虚拟环境已存在，跳过创建
) else (
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo [SUCCESS] 虚拟环境创建完成: %VENV_DIR%
)

:: 激活虚拟环境
echo [INFO] 激活虚拟环境...
call "%VENV_DIR%\Scripts\activate.bat"
echo [SUCCESS] 虚拟环境已激活

:: 升级pip
echo [INFO] 升级pip...
python -m pip install --upgrade pip

:: 安装依赖
echo [INFO] 安装项目依赖...

if exist "requirements.txt" (
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] 依赖安装失败
        pause
        exit /b 1
    )
    echo [SUCCESS] 依赖安装完成
) else (
    echo [WARNING] 未找到requirements.txt，跳过依赖安装
)

:: 安装包到全局
echo [INFO] 安装AIDefectDetector到全局...

pip install -e .
if errorlevel 1 (
    echo [ERROR] pip安装失败，尝试创建全局链接...

    :: 备用方案：创建全局脚本
    set SCRIPT_DIR=%~dp0
    set GLOBAL_SCRIPT=%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\aidefect.bat

    echo @echo off > "%GLOBAL_SCRIPT%"
    echo "%SCRIPT_DIR%aidefect" %%* >> "%GLOBAL_SCRIPT%"

    echo [SUCCESS] 全局脚本创建成功: %GLOBAL_SCRIPT%
) else (
    echo [SUCCESS] AIDefectDetector安装成功！
)

:: 创建配置文件
echo [INFO] 创建配置文件...

set CONFIG_DIR=%USERPROFILE%\.aidefect
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"

if not exist "%CONFIG_DIR%\config.yaml" (
    if exist "config\user_config.example.yaml" (
        copy "config\user_config.example.yaml" "%CONFIG_DIR%\config.yaml" >nul
        echo [SUCCESS] 配置文件已创建: %CONFIG_DIR%\config.yaml
        echo [INFO] 请编辑配置文件添加你的API密钥
    ) else (
        echo [WARNING] 未找到配置模板文件
    )
) else (
    echo [WARNING] 配置文件已存在，跳过创建
)

:: 验证安装
echo [INFO] 验证安装...

aidefect --help >nul 2>&1
if errorlevel 1 (
    echo [WARNING] aidefect 命令不可用
) else (
    echo [SUCCESS] aidefect 命令测试通过
)

aidefect-web --help >nul 2>&1
if errorlevel 1 (
    echo [WARNING] aidefect-web 命令不可用（可能缺少Flask依赖）
) else (
    echo [SUCCESS] aidefect-web 命令可用
)

:: 显示使用说明
echo.
echo [SUCCESS] 安装完成！
echo.
echo 🎯 使用方法：
echo   aidefect              - 启动CLI模式
echo   aidefect --help      - 显示帮助信息
echo   aidefect-web         - 启动Web界面（如果可用）
echo.
echo 📁 配置文件：
echo   %USERPROFILE%\.aidefect\config.yaml
echo.
echo 📚 更多信息：
echo   查看 QUICKSTART.md  - 快速开始指南
echo   查看 README.md      - 完整文档
echo.
echo 💡 提示：
echo   如需卸载，请运行: pip uninstall aidefect
echo.

pause
echo [SUCCESS] AIDefectDetector安装完成！