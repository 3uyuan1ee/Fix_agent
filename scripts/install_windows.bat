@echo off
:: AIDefectDetector Windows 统一安装脚本
:: 合并了原有的 install.bat 和相关功能

setlocal enabledelayedexpansion

:: 设置代码页为UTF-8
chcp 65001 >nul

:: 颜色定义（Windows 10+支持ANSI转义序列）
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "CYAN=[96m"
set "NC=[0m"

:: 打印带颜色的消息
:print_info
echo %BLUE%ℹ️  %~1%NC%
goto :eof

:print_success
echo %GREEN%✅ %~1%NC%
goto :eof

:print_warning
echo %YELLOW%⚠️  %~1%NC%
goto :eof

:print_error
echo %RED%❌ %~1%NC%
goto :eof

:print_header
echo %CYAN%
echo %~1
echo ==================================================
echo %NC%
goto :eof

:: 显示标题
call :print_header "🚀 AIDefectDetector Windows 安装脚本"

:: 切换到项目根目录
cd /d "%~dp0\.."
:: 设置项目目录变量供后续使用
set "PROJECT_DIR=%CD%"
call :print_info "项目目录: %PROJECT_DIR%"

:: 检查管理员权限
:check_admin
call :print_info "检查管理员权限..."
net session >nul 2>&1
if %errorlevel% == 0 (
    call :print_success "检测到管理员权限"
    set "HAS_ADMIN=1"
) else (
    call :print_warning "未检测到管理员权限，某些功能可能受限"
    set "HAS_ADMIN=0"
)

:: 检查Python版本
:check_python
call :print_info "检查Python环境..."

:: 检查python命令
python --version >nul 2>&1
if errorlevel 1 (
    :: 检查python3命令
    python3 --version >nul 2>&1
    if errorlevel 1 (
        call :print_error "Python 未安装，请先安装Python 3.8+"
        call :print_info "下载地址: https://www.python.org/downloads/"
        call :print_info "或者使用 Microsoft Store: python"
        pause
        exit /b 1
    ) else (
        set "PYTHON_CMD=python3"
        set "PIP_CMD=pip3"
    )
) else (
    set "PYTHON_CMD=python"
    set "PIP_CMD=pip"
)

:: 获取Python版本
for /f "tokens=2" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%i

:: 检查版本是否满足要求
%PYTHON_CMD% -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if errorlevel 1 (
    call :print_error "Python版本过低: %PYTHON_VERSION%，需要3.8+"
    call :print_info "请升级Python: https://www.python.org/downloads/"
    pause
    exit /b 1
) else (
    call :print_success "Python版本检查通过: %PYTHON_VERSION%"
)

:: 检查pip
:check_pip
call :print_info "检查pip..."

%PIP_CMD% --version >nul 2>&1
if errorlevel 1 (
    call :print_error "pip 未安装，请确保pip已正确安装"
    call :print_info "尝试修复pip: python -m ensurepip --upgrade"
    pause
    exit /b 1
) else (
    call :print_success "pip检查通过"
)

:: 安装系统依赖
:install_system_deps
call :print_info "检查系统依赖..."

:: 检查git
git --version >nul 2>&1
if errorlevel 1 (
    call :print_warning "Git 未安装，建议安装Git for Windows"
    call :print_info "下载地址: https://git-scm.com/download/win"
) else (
    call :print_success "Git 已安装"
)

:: 检查curl（Windows 10+内置）
curl --version >nul 2>&1
if errorlevel 1 (
    call :print_warning "curl 不可用，某些功能可能受限"
) else (
    call :print_success "curl 可用"
)

:: 创建虚拟环境
:create_venv
call :print_info "创建虚拟环境..."

set "VENV_DIR=%USERPROFILE%\.aidefect_venv"

if exist "%VENV_DIR%" (
    call :print_warning "虚拟环境已存在，检查是否需要重新创建..."
    set /p "recreate_venv=是否重新创建虚拟环境? (y/N): "
    if /i "!recreate_venv!"=="y" (
        rmdir /s /q "%VENV_DIR%" >nul 2>&1
        if exist "%VENV_DIR%" (
            call :print_error "无法删除旧虚拟环境，请手动删除: %VENV_DIR%"
            pause
            exit /b 1
        ) else (
            call :print_info "已删除旧虚拟环境"
        )
    ) else (
        call :print_success "使用现有虚拟环境"
    )
)

if not exist "%VENV_DIR%" (
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        call :print_error "虚拟环境创建失败"
        pause
        exit /b 1
    ) else (
        call :print_success "虚拟环境创建完成: %VENV_DIR%"
    )
)

:: 激活虚拟环境
call :print_info "激活虚拟环境..."
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    call :print_error "虚拟环境激活失败"
    pause
    exit /b 1
) else (
    call :print_success "虚拟环境已激活"
)

:: 升级pip和安装基础工具
:upgrade_pip
call :print_info "升级pip和安装基础工具..."

:: 升级pip
python -m pip install --upgrade pip
if errorlevel 1 (
    call :print_warning "pip升级失败，继续使用现有版本"
)

:: 安装基础工具
python -m pip install wheel setuptools
if errorlevel 1 (
    call :print_warning "基础工具安装失败，继续安装..."
)

call :print_success "pip升级完成"

:: 安装依赖
:install_dependencies
call :print_info "安装项目依赖..."

if exist "requirements.txt" (
    :: 检查是否有requirements-lock.txt
    if exist "requirements-lock.txt" (
        call :print_info "发现锁定依赖文件，使用 requirements-lock.txt"
        pip install -r requirements-lock.txt
    ) else (
        pip install -r requirements.txt
    )

    if errorlevel 1 (
        call :print_error "依赖安装失败"
        pause
        exit /b 1
    ) else (
        call :print_success "依赖安装完成"
    )
) else (
    call :print_warning "未找到requirements.txt，尝试安装核心依赖..."

    :: 安装核心依赖
    pip install pyyaml loguru requests
    if errorlevel 1 (
        call :print_warning "核心依赖安装失败，继续安装..."
    ) else (
        call :print_success "核心依赖安装完成"
    )
)

:: 安装包到环境
:install_package
call :print_info "安装AIDefectDetector..."

:: 开发模式安装
pip install -e .
if errorlevel 1 (
    call :print_error "pip安装失败，尝试其他方式..."
    goto :create_global_scripts
) else (
    call :print_success "AIDefectDetector安装成功！"
)

:: 创建全局脚本
:create_global_scripts
call :print_info "创建全局命令脚本..."

:: 设置脚本目录
set "SCRIPT_DIR=%USERPROFILE%\AppData\Local\Microsoft\WindowsApps"
if not exist "%SCRIPT_DIR%" (
    mkdir "%SCRIPT_DIR%" >nul 2>&1
)

:: 创建 aidefect.bat 脚本
set "AIDEFECT_SCRIPT=%SCRIPT_DIR%\aidefect.bat"
(
echo @echo off
echo :: AIDefectDetector wrapper script
echo call "%VENV_DIR%\Scripts\activate.bat"
echo cd /d "%PROJECT_DIR%"
echo python main.py %%*
) > "%AIDEFECT_SCRIPT%"

if exist "%AIDEFECT_SCRIPT%" (
    call :print_success "aidefect 全局脚本创建成功: %AIDEFECT_SCRIPT%"
) else (
    call :print_warning "aidefect 全局脚本创建失败"
)

:: 创建 aidefect-web.bat 脚本
set "AIDEFECT_WEB_SCRIPT=%SCRIPT_DIR%\aidefect-web.bat"
(
echo @echo off
echo :: AIDefectDetector Web wrapper script
echo call "%VENV_DIR%\Scripts\activate.bat"
echo cd /d "%PROJECT_DIR%"
echo python main.py web %%*
) > "%AIDEFECT_WEB_SCRIPT%"

if exist "%AIDEFECT_WEB_SCRIPT%" (
    call :print_success "aidefect-web 全局脚本创建成功: %AIDEFECT_WEB_SCRIPT%"
) else (
    call :print_warning "aidefect-web 全局脚本创建失败"
)

:: 创建配置文件
:create_config
call :print_info "创建配置文件..."

set "CONFIG_DIR=%USERPROFILE%\.aidefect"
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"

:: 创建用户配置文件
if not exist "%CONFIG_DIR%\config.yaml" (
    if exist "config\user_config.example.yaml" (
        copy "config\user_config.example.yaml" "%CONFIG_DIR%\config.yaml" >nul
        call :print_success "配置文件已创建: %CONFIG_DIR%\config.yaml"
    ) else if exist "config\examples\minimal.yaml" (
        copy "config\examples\minimal.yaml" "%CONFIG_DIR%\config.yaml" >nul
        call :print_success "配置文件已创建: %CONFIG_DIR%\config.yaml"
    ) else (
        :: 创建基础配置文件
        (
            echo # AIDefectDetector 配置文件
            echo llm:
            echo   default_provider: mock
            echo   mock:
            echo     provider: mock
            echo     model: mock-model
            echo     api_base: "http://mock-api"
            echo     max_tokens: 4000
            echo     temperature: 0.1
            echo.
            echo cache:
            echo   enabled: true
            echo   directory: "%CONFIG_DIR%\cache"
            echo   max_size: 100
            echo.
            echo logging:
            echo   level: INFO
            echo   file: "%CONFIG_DIR%\logs\aidefect.log"
        ) > "%CONFIG_DIR%\config.yaml"
        call :print_success "基础配置文件已创建: %CONFIG_DIR%\config.yaml"
    )
    call :print_info "请编辑配置文件以添加您的API密钥"
) else (
    call :print_warning "配置文件已存在，跳过创建"
)

:: 创建.env文件
if not exist "%CONFIG_DIR%\.env" (
    (
        echo # AIDefectDetector 环境变量
        echo # 请在此处添加您的API密钥
        echo.
        echo # 智谱AI ^(推荐国内用户^)
        echo # ZHIPU_API_KEY=your-zhipu-api-key
        echo.
        echo # OpenAI
        echo # OPENAI_API_KEY=your-openai-api-key
        echo # OPENAI_BASE_URL=https://api.openai.com/v1
        echo.
        echo # Anthropic
        echo # ANTHROPIC_API_KEY=your-anthropic-api-key
        echo # ANTHROPIC_BASE_URL=https://api.anthropic.com
    ) > "%CONFIG_DIR%\.env"
    call :print_success "环境变量文件已创建: %CONFIG_DIR%\.env"
) else (
    call :print_warning "环境变量文件已存在，跳过创建"
)

:: 验证安装
:verify_installation
call :print_info "验证安装..."

:: 检查Python模块导入
python -c "import sys; sys.path.insert(0, 'src'); from interfaces.cli import cli_main; print('✅ 模块导入成功')" >nul 2>&1
if errorlevel 1 (
    call :print_warning "Python模块导入测试失败"
) else (
    call :print_success "Python模块导入测试通过"
)

:: 检查配置文件
if exist "%CONFIG_DIR%\config.yaml" (
    call :print_success "配置文件存在"
) else (
    call :print_error "配置文件不存在"
)

:: 检查主程序
if exist "main.py" (
    call :print_success "主程序文件存在"

    :: 测试帮助命令（超时保护）
    timeout /t 10 /nobreak >nul 2>&1 & python main.py --help >nul 2>&1
    if errorlevel 1 (
        call :print_warning "主程序帮助命令测试失败"
    ) else (
        call :print_success "主程序帮助命令测试通过"
    )
) else (
    call :print_error "主程序文件不存在"
)

:: 显示使用说明
:show_usage
call :print_header "🎯 安装完成！使用方法"

echo %GREEN%基本命令：%NC%
echo   %BLUE%python main.py%NC%              - 启动CLI模式
echo   %BLUE%python main.py --help%NC%       - 显示帮助信息
echo   %BLUE%python main.py web%NC%          - 启动Web界面
echo.

if exist "%AIDEFECT_SCRIPT%" (
    echo %GREEN%全局命令：%NC%
    echo   %BLUE%aidefect%NC%                 - 启动CLI模式
    echo   %BLUE%aidefect --help%NC%          - 显示帮助信息
    echo   %BLUE%aidefect-web%NC%             - 启动Web界面
    echo.
)

echo %GREEN%配置文件：%NC%
echo   %BLUE%%CONFIG_DIR%\config.yaml%NC%    - 主配置文件
echo   %BLUE%%CONFIG_DIR%\.env%NC%           - 环境变量文件
echo.

echo %GREEN%快速配置API：%NC%
echo   %BLUE%python scripts\configure_llm.py%NC% - LLM配置向导
echo.

echo %GREEN%故障诊断：%NC%
echo   %BLUE%python scripts\diagnose_config.py%NC% - 配置诊断
echo.

echo %YELLOW%💡 下一步：%NC%
echo   1. 配置API密钥: %BLUE%python scripts\configure_llm.py%NC%
echo   2. 运行诊断: %BLUE%python scripts\diagnose_config.py%NC%
echo   3. 开始使用: %BLUE%python main.py analyze deep src\utils\config.py%NC%
echo.

echo %YELLOW%📚 文档：%NC%
echo   %BLUE%docs\README.md%NC%              - 完整文档
echo   %BLUE%docs\API_CONFIG_GUIDE.md%NC%     - API配置指南
echo.

echo %YELLOW%🗑️  卸载：%NC%
echo   删除虚拟环境: %BLUE%rmdir /s /q %VENV_DIR%%NC%
echo   删除配置文件: %BLUE%rmdir /s /q %CONFIG_DIR%%NC%
echo   删除全局脚本: %BLUE%del %AIDEFECT_SCRIPT%%NC%

:: 结束
echo.
call :print_success "AIDefectDetector安装完成！"
echo.
pause