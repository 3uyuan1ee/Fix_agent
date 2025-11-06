#!/bin/bash
# AIDefectDetector Unix/Linux/macOS 统一安装脚本


set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${CYAN}"
    echo "$1"
    echo "$(printf '=%.0s' {1..50})"
    echo -e "${NC}"
}

# 显示标题
print_header "🚀 AIDefectDetector Unix/Linux/macOS 安装脚本"

# 检查操作系统
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="Linux"
        if command -v apt-get &> /dev/null; then
            DISTRO="Ubuntu/Debian"
        elif command -v yum &> /dev/null; then
            DISTRO="CentOS/RHEL"
        elif command -v dnf &> /dev/null; then
            DISTRO="Fedora"
        else
            DISTRO="Unknown Linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macOS"
        DISTRO="macOS"
    else
        OS="Unknown"
        DISTRO="Unknown"
    fi

    print_info "检测到操作系统: $OS ($DISTRO)"
}

# 检查Python版本
check_python() {
    print_info "检查Python环境..."

    # 优先使用python3
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        PIP_CMD="pip3"
    elif command -v python &> /dev/null; then
        # 检查python版本是否满足要求
        python_version=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        if python -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
            PYTHON_CMD="python"
            PIP_CMD="pip"
        else
            print_error "系统Python版本过低: $python_version，需要3.8+"
            print_info "请安装Python 3.8+:"
            if [[ "$OS" == "Linux" ]]; then
                if [[ "$DISTRO" == "Ubuntu/Debian" ]]; then
                    print_info "  sudo apt update && sudo apt install python3 python3-pip python3-venv"
                elif [[ "$DISTRO" == "CentOS/RHEL" ]]; then
                    print_info "  sudo yum install python3 python3-pip"
                elif [[ "$DISTRO" == "Fedora" ]]; then
                    print_info "  sudo dnf install python3 python3-pip"
                fi
            elif [[ "$OS" == "macOS" ]]; then
                print_info "  brew install python@3.11"
            fi
            exit 1
        fi
    else
        print_error "Python未安装，请先安装Python 3.8+"
        exit 1
    fi

    python_version=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if $PYTHON_CMD -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        print_success "Python版本检查通过: $python_version"
    else
        print_error "Python版本过低: $python_version，需要3.8+"
        exit 1
    fi
}

# 检查pip
check_pip() {
    print_info "检查pip..."

    if ! command -v $PIP_CMD &> /dev/null; then
        print_error "pip未安装，请先安装pip"
        if [[ "$OS" == "Linux" ]]; then
            if [[ "$DISTRO" == "Ubuntu/Debian" ]]; then
                print_info "  sudo apt install python3-pip"
            elif [[ "$DISTRO" == "CentOS/RHEL" ]]; then
                print_info "  sudo yum install python3-pip"
            elif [[ "$DISTRO" == "Fedora" ]]; then
                print_info "  sudo dnf install python3-pip"
            fi
        fi
        exit 1
    fi

    print_success "pip检查通过"
}

# 安装系统依赖
install_system_deps() {
    print_info "检查系统依赖..."

    if [[ "$OS" == "Linux" ]]; then
        # 检查并安装基础工具
        local missing_deps=()

        for cmd in git curl wget; do
            if ! command -v $cmd &> /dev/null; then
                missing_deps+=($cmd)
            fi
        done

        if [[ ${#missing_deps[@]} -gt 0 ]]; then
            print_warning "缺少系统依赖: ${missing_deps[*]}"
            print_info "尝试安装缺少的依赖..."

            if [[ "$DISTRO" == "Ubuntu/Debian" ]]; then
                if command -v sudo &> /dev/null; then
                    sudo apt update && sudo apt install -y ${missing_deps[*]}
                else
                    print_warning "无sudo权限，请手动安装: ${missing_deps[*]}"
                fi
            elif [[ "$DISTRO" == "CentOS/RHEL" ]]; then
                if command -v sudo &> /dev/null; then
                    sudo yum install -y ${missing_deps[*]}
                else
                    print_warning "无sudo权限，请手动安装: ${missing_deps[*]}"
                fi
            elif [[ "$DISTRO" == "Fedora" ]]; then
                if command -v sudo &> /dev/null; then
                    sudo dnf install -y ${missing_deps[*]}
                else
                    print_warning "无sudo权限，请手动安装: ${missing_deps[*]}"
                fi
            fi
        fi
    elif [[ "$OS" == "macOS" ]]; then
        # 检查是否有Homebrew
        if ! command -v brew &> /dev/null; then
            print_info "建议安装Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        fi

        # 检查Xcode命令行工具
        if ! xcode-select -p &> /dev/null; then
            print_info "安装Xcode命令行工具..."
            xcode-select --install 2>/dev/null || print_warning "Xcode命令行工具可能需要手动安装"
        fi
    fi

    print_success "系统依赖检查完成"
}

# 创建虚拟环境
create_venv() {
    print_info "创建虚拟环境..."

    VENV_DIR="$HOME/.aidefect_venv"

    if [ -d "$VENV_DIR" ]; then
        print_warning "虚拟环境已存在，检查是否需要重新创建..."
        read -p "是否重新创建虚拟环境? (y/N): " recreate_venv
        if [[ "$recreate_venv" =~ ^[Yy]$ ]]; then
            rm -rf "$VENV_DIR"
            print_info "已删除旧虚拟环境"
        else
            print_success "使用现有虚拟环境"
        fi
    fi

    if [ ! -d "$VENV_DIR" ]; then
        $PYTHON_CMD -m venv "$VENV_DIR"
        if [ $? -eq 0 ]; then
            print_success "虚拟环境创建完成: $VENV_DIR"
        else
            print_error "虚拟环境创建失败"
            exit 1
        fi
    fi

    # 激活虚拟环境
    source "$VENV_DIR/bin/activate"
    if [ $? -eq 0 ]; then
        print_success "虚拟环境已激活"
    else
        print_error "虚拟环境激活失败"
        exit 1
    fi
}

# 升级pip和安装基础工具
upgrade_pip() {
    print_info "升级pip和安装基础工具..."

    # 升级pip
    python -m pip install --upgrade pip

    # 安装基础工具
    python -m pip install wheel setuptools

    print_success "pip升级完成"
}

# 安装依赖
install_dependencies() {
    print_info "安装项目依赖..."

    if [ -f "requirements.txt" ]; then
        # 检查是否有requirements-lock.txt
        if [ -f "requirements-lock.txt" ]; then
            print_info "发现锁定依赖文件，使用 requirements-lock.txt"
            pip install -r requirements-lock.txt
        else
            pip install -r requirements.txt
        fi

        if [ $? -eq 0 ]; then
            print_success "依赖安装完成"
        else
            print_error "依赖安装失败"
            exit 1
        fi
    else
        print_warning "未找到requirements.txt，尝试安装核心依赖..."

        # 安装核心依赖
        pip install pyyaml loguru requests asyncio
        print_success "核心依赖安装完成"
    fi
}

# 安装包到环境
install_package() {
    print_info "安装AIDefectDetector..."

    # 开发模式安装
    pip install -e .

    if [ $? -eq 0 ]; then
        print_success "AIDefectDetector安装成功！"
        return 0
    else
        print_error "pip安装失败，尝试其他方式..."
        return 1
    fi
}

# 创建全局符号链接
create_global_symlinks() {
    print_info "创建全局命令链接..."

    VENV_BIN="$VENV_DIR/bin"

    # 确定本地bin目录
    LOCAL_BIN=""
    if [ -d "/usr/local/bin" ] && [ -w "/usr/local/bin" ]; then
        LOCAL_BIN="/usr/local/bin"
    elif [ -d "$HOME/.local/bin" ]; then
        LOCAL_BIN="$HOME/.local/bin"
        mkdir -p "$LOCAL_BIN"
    else
        LOCAL_BIN="$HOME/.local/bin"
        mkdir -p "$LOCAL_BIN"
    fi

    # 创建 aidefect 链接
    if [ -f "$VENV_BIN/python" ] ; then
        # 创建wrapper脚本
        cat > "$LOCAL_BIN/aidefect" << EOF
#!/bin/bash
# AIDefectDetector wrapper script
source "$VENV_DIR/bin/activate"
cd "$PROJECT_DIR"
exec python main.py "\$@"
EOF
        chmod +x "$LOCAL_BIN/aidefect"
        print_success "aidefect 全局链接创建成功: $LOCAL_BIN/aidefect"
    fi

    # 创建 aidefect-web 链接
    cat > "$LOCAL_BIN/aidefect-web" << EOF
#!/bin/bash
# AIDefectDetector Web wrapper script
source "$VENV_DIR/bin/activate"
cd "$PROJECT_DIR"
exec python main.py web "\$@"
EOF
    chmod +x "$LOCAL_BIN/aidefect-web"
    print_success "aidefect-web 全局链接创建成功: $LOCAL_BIN/aidefect-web"

    # 提示添加到 PATH
    if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
        print_info "请将 $LOCAL_BIN 添加到您的 PATH 环境变量中"

        # 检测shell类型
        if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
            print_info "可以运行以下命令："
            print_info "  echo 'export PATH=\$PATH:$LOCAL_BIN' >> ~/.zshrc"
            print_info "  source ~/.zshrc"
        elif [ -f "$HOME/.bashrc" ]; then
            print_info "可以运行以下命令："
            print_info "  echo 'export PATH=\$PATH:$LOCAL_BIN' >> ~/.bashrc"
            print_info "  source ~/.bashrc"
        fi
    fi
}

# 创建配置文件
create_config() {
    print_info "创建配置文件..."

    CONFIG_DIR="$HOME/.aidefect"
    mkdir -p "$CONFIG_DIR"

    # 创建用户配置文件
    if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
        if [ -f "config/user_config.example.yaml" ]; then
            cp "config/user_config.example.yaml" "$CONFIG_DIR/config.yaml"
            print_success "配置文件已创建: $CONFIG_DIR/config.yaml"
        elif [ -f "config/examples/minimal.yaml" ]; then
            cp "config/examples/minimal.yaml" "$CONFIG_DIR/config.yaml"
            print_success "配置文件已创建: $CONFIG_DIR/config.yaml"
        else
            # 创建基础配置文件
            cat > "$CONFIG_DIR/config.yaml" << EOF
# AIDefectDetector 配置文件
llm:
  default_provider: mock
  mock:
    provider: mock
    model: mock-model
    api_base: "http://mock-api"
    max_tokens: 4000
    temperature: 0.1

cache:
  enabled: true
  directory: "$CONFIG_DIR/cache"
  max_size: 100

logging:
  level: INFO
  file: "$CONFIG_DIR/logs/aidefect.log"
EOF
            print_success "基础配置文件已创建: $CONFIG_DIR/config.yaml"
        fi
        print_info "请编辑配置文件以添加您的API密钥"
    else
        print_warning "配置文件已存在，跳过创建"
    fi

    # 创建.env文件
    if [ ! -f "$CONFIG_DIR/.env" ]; then
        cat > "$CONFIG_DIR/.env" << EOF
# AIDefectDetector 环境变量
# 请在此处添加您的API密钥

# 智谱AI (推荐国内用户)
# ZHIPU_API_KEY=your-zhipu-api-key

# OpenAI
# OPENAI_API_KEY=your-openai-api-key
# OPENAI_BASE_URL=https://api.openai.com/v1

# Anthropic
# ANTHROPIC_API_KEY=your-anthropic-api-key
# ANTHROPIC_BASE_URL=https://api.anthropic.com
EOF
        print_success "环境变量文件已创建: $CONFIG_DIR/.env"
    else
        print_warning "环境变量文件已存在，跳过创建"
    fi
}

# 验证安装
verify_installation() {
    print_info "验证安装..."

    # 检查Python模块导入
    if python -c "import sys; sys.path.insert(0, 'src'); from interfaces.cli import cli_main; print('✅ 模块导入成功')" 2>/dev/null; then
        print_success "Python模块导入测试通过"
    else
        print_warning "Python模块导入测试失败"
    fi

    # 检查配置文件
    if [ -f "$CONFIG_DIR/config.yaml" ]; then
        print_success "配置文件存在"
    else
        print_error "配置文件不存在"
    fi

    # 检查主程序
    if [ -f "main.py" ]; then
        print_success "主程序文件存在"

        # 测试帮助命令
        if timeout 10 python main.py --help &>/dev/null; then
            print_success "主程序帮助命令测试通过"
        else
            print_warning "主程序帮助命令测试失败"
        fi
    else
        print_error "主程序文件不存在"
    fi
}

# 显示使用说明
show_usage() {
    print_header "🎯 安装完成！使用方法"

    echo -e "${GREEN}基本命令：${NC}"
    echo -e "  ${BLUE}python main.py${NC}              - 启动CLI模式"
    echo -e "  ${BLUE}python main.py --help${NC}       - 显示帮助信息"
    echo -e "  ${BLUE}python main.py web${NC}          - 启动Web界面"
    echo ""

    if command -v aidefect &> /dev/null; then
        echo -e "${GREEN}全局命令：${NC}"
        echo -e "  ${BLUE}aidefect${NC}                 - 启动CLI模式"
        echo -e "  ${BLUE}aidefect --help${NC}          - 显示帮助信息"
        echo -e "  ${BLUE}aidefect-web${NC}             - 启动Web界面"
        echo ""
    fi

    echo -e "${GREEN}配置文件：${NC}"
    echo -e "  ${BLUE}$CONFIG_DIR/config.yaml${NC}     - 主配置文件"
    echo -e "  ${BLUE}$CONFIG_DIR/.env${NC}            - 环境变量文件"
    echo ""

    echo -e "${GREEN}快速配置API：${NC}"
    echo -e "  ${BLUE}python scripts/configure_llm.py${NC} - LLM配置向导"
    echo ""

    echo -e "${GREEN}故障诊断：${NC}"
    echo -e "  ${BLUE}python scripts/diagnose_config.py${NC} - 配置诊断"
    echo ""

    echo -e "${YELLOW}💡 下一步：${NC}"
    echo -e "  1. 配置API密钥: ${BLUE}python scripts/configure_llm.py${NC}"
    echo -e "  2. 运行诊断: ${BLUE}python scripts/diagnose_config.py${NC}"
    echo -e "  3. 开始使用: ${BLUE}python main.py analyze deep src/utils/config.py${NC}"
    echo ""

    echo -e "${YELLOW}📚 文档：${NC}"
    echo -e "  ${BLUE}docs/README.md${NC}              - 完整文档"
    echo -e "  ${BLUE}docs/API_CONFIG_GUIDE.md${NC}     - API配置指南"
    echo ""

    echo -e "${YELLOW}🗑️  卸载：${NC}"
    echo -e "  删除虚拟环境: ${BLUE}rm -rf $VENV_DIR${NC}"
    echo -e "  删除配置文件: ${BLUE}rm -rf $CONFIG_DIR${NC}"
    echo -e "  删除全局链接: ${BLUE}rm /usr/local/bin/aidefect*${NC}"
}

# 主安装流程
main() {
    print_info "开始安装AIDefectDetector..."
    echo

    # 进入项目根目录（scripts目录的上一级）
    cd "$(dirname "$(dirname "${BASH_SOURCE[0]}")")"

    # 设置项目目录变量供后续使用
    PROJECT_DIR="$(pwd)"
    print_info "项目目录: $PROJECT_DIR"

    # 执行安装步骤
    detect_os
    check_python
    check_pip
    install_system_deps
    create_venv
    upgrade_pip
    install_dependencies
    install_package
    create_global_symlinks
    create_config
    verify_installation
    show_usage

    print_success "AIDefectDetector安装完成！"
}

# 错误处理
trap 'print_error "安装过程中发生错误，请检查上面的错误信息"; exit 1' ERR

# 运行主程序
main "$@"