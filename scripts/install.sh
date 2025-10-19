#!/bin/bash
# AIDefectDetector 全局安装脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# 显示标题
echo -e "${BLUE}"
echo "🚀 AIDefectDetector 全局安装脚本"
echo "===================================="
echo -e "${NC}"

# 检查Python版本
check_python() {
    print_info "检查Python环境..."

    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未安装，请先安装Python 3.8+"
        exit 1
    fi

    python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    min_version="3.8"

    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        print_success "Python版本检查通过: $python_version"
    else
        print_error "Python版本过低: $python_version，需要3.8+"
        exit 1
    fi
}

# 检查pip
check_pip() {
    print_info "检查pip..."

    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 未安装，请先安装pip"
        exit 1
    fi

    print_success "pip检查通过"
}

# 创建虚拟环境
create_venv() {
    print_info "创建虚拟环境..."

    VENV_DIR="$HOME/.aidefect_venv"

    if [ -d "$VENV_DIR" ]; then
        print_warning "虚拟环境已存在，跳过创建"
    else
        python3 -m venv "$VENV_DIR"
        print_success "虚拟环境创建完成: $VENV_DIR"
    fi

    # 激活虚拟环境
    source "$VENV_DIR/bin/activate"
    print_success "虚拟环境已激活"
}

# 安装依赖
install_dependencies() {
    print_info "安装项目依赖..."

    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "依赖安装完成"
    else
        print_warning "未找到requirements.txt，跳过依赖安装"
    fi
}

# 安装包到全局
install_package() {
    print_info "安装AIDefectDetector到全局..."

    # 开发模式安装
    pip install -e .

    if [ $? -eq 0 ]; then
        print_success "AIDefectDetector安装成功！"

        # 创建全局符号链接
        create_global_symlinks
    else
        print_error "安装失败，尝试使用可执行脚本方式..."

        # 备用方案：创建全局链接
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        GLOBAL_SCRIPT="/usr/local/bin/aidefect"

        if [ -w "/usr/local/bin" ]; then
            cp "$SCRIPT_DIR/aidefect" "$GLOBAL_SCRIPT"
            chmod +x "$GLOBAL_SCRIPT"
            print_success "全局链接创建成功: $GLOBAL_SCRIPT"
        else
            print_warning "需要管理员权限创建全局链接"
            print_info "请运行: sudo cp $SCRIPT_DIR/aidefect /usr/local/bin/aidefect"
            print_info "然后: sudo chmod +x /usr/local/bin/aidefect"
        fi
    fi
}

# 创建全局符号链接
create_global_symlinks() {
    print_info "创建全局命令链接..."

    VENV_BIN="$VENV_DIR/bin"
    LOCAL_BIN="/usr/local/bin"

    if [ ! -d "$LOCAL_BIN" ]; then
        print_warning "$LOCAL_BIN 目录不存在，尝试创建..."
        sudo mkdir -p "$LOCAL_BIN" 2>/dev/null || {
            print_warning "无法创建 $LOCAL_BIN，将在用户目录创建链接"
            LOCAL_BIN="$HOME/.local/bin"
            mkdir -p "$LOCAL_BIN"
        }
    fi

    # 检查是否有写入权限
    if [ -w "$LOCAL_BIN" ]; then
        # 创建 aidefect 链接
        if [ -f "$VENV_BIN/aidefect" ]; then
            ln -sf "$VENV_BIN/aidefect" "$LOCAL_BIN/aidefect"
            print_success "aidefect 全局链接创建成功"
        fi

        # 创建 aidefect-web 链接
        if [ -f "$VENV_BIN/aidefect-web" ]; then
            ln -sf "$VENV_BIN/aidefect-web" "$LOCAL_BIN/aidefect-web"
            print_success "aidefect-web 全局链接创建成功"
        fi

        # 提示添加到 PATH
        if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
            print_info "请将 $LOCAL_BIN 添加到您的 PATH 环境变量中"
            print_info "可以运行以下命令："
            print_info "  echo 'export PATH=\$PATH:$LOCAL_BIN' >> ~/.zshrc"
            print_info "  source ~/.zshrc"
        fi
    else
        print_warning "需要管理员权限创建全局链接"
        print_info "请运行以下命令创建链接："
        print_info "  sudo ln -sf $VENV_BIN/aidefect $LOCAL_BIN/aidefect"
        print_info "  sudo ln -sf $VENV_BIN/aidefect-web $LOCAL_BIN/aidefect-web"
    fi
}

# 创建配置文件
create_config() {
    print_info "创建配置文件..."

    CONFIG_DIR="$HOME/.aidefect"
    mkdir -p "$CONFIG_DIR"

    if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
        if [ -f "config/user_config.example.yaml" ]; then
            cp "config/user_config.example.yaml" "$CONFIG_DIR/config.yaml"
            print_success "配置文件已创建: $CONFIG_DIR/config.yaml"
            print_info "请编辑配置文件添加你的API密钥"
        else
            print_warning "未找到配置模板文件"
        fi
    else
        print_warning "配置文件已存在，跳过创建"
    fi
}

# 验证安装
verify_installation() {
    print_info "验证安装..."

    # 检查命令是否可用
    if command -v aidefect &> /dev/null; then
        print_success "aidefect 命令可用"

        # 测试帮助命令
        if aidefect --help &> /dev/null; then
            print_success "aidefect 命令测试通过"
        else
            print_warning "aidefect 命令测试失败"
        fi
    else
        print_error "aidefect 命令不可用"
        return 1
    fi

    # 检查web命令
    if command -v aidefect-web &> /dev/null; then
        print_success "aidefect-web 命令可用"
    else
        print_warning "aidefect-web 命令不可用（可能缺少Flask依赖）"
    fi
}

# 显示使用说明
show_usage() {
    print_success "安装完成！"
    echo
    echo -e "${GREEN}🎯 使用方法：${NC}"
    echo -e "  ${BLUE}aidefect${NC}              - 启动CLI模式"
    echo -e "  ${BLUE}aidefect --help${NC}      - 显示帮助信息"
    echo -e "  ${BLUE}aidefect-web${NC}         - 启动Web界面（如果可用）"
    echo
    echo -e "${GREEN}📁 配置文件：${NC}"
    echo -e "  ${BLUE}$HOME/.aidefect/config.yaml${NC}"
    echo
    echo -e "${GREEN}📚 更多信息：${NC}"
    echo -e "  ${BLUE}查看 docs/QUICKSTART.md${NC}  - 快速开始指南"
    echo -e "  ${BLUE}查看 docs/README.md${NC}      - 完整文档"
    echo -e "  ${BLUE}查看 docs/INSTALL.md${NC}      - 安装指南"
    echo
    echo -e "${YELLOW}💡 提示：${NC}"
    echo -e "  如需卸载，请运行: ${BLUE}pip uninstall aidefect${NC}"
    echo -e "  或手动删除: ${BLUE}sudo rm /usr/local/bin/aidefect${NC}"
}

# 主安装流程
main() {
    echo "开始安装AIDefectDetector..."
    echo

    # 进入项目根目录（scripts目录的上一级）
    cd "$(dirname "$(dirname "${BASH_SOURCE[0]}")")"

    # 执行安装步骤
    check_python
    check_pip
    create_venv
    install_dependencies
    install_package
    create_config
    verify_installation
    show_usage

    print_success "AIDefectDetector安装完成！"
}

# 错误处理
trap 'print_error "安装过程中发生错误，请检查上面的错误信息"; exit 1' ERR

# 运行主程序
main "$@"