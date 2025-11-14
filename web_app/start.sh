#!/bin/bash

# Fix Agent Web 应用启动脚本
# 提供友好的启动体验和自动检查

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    echo -e "${GREEN}${BOLD}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_header() {
    echo -e "${CYAN}${BOLD}"
    echo "🤖 Fix Agent Web 应用"
    echo "===================="
    echo -e "${NC}"
}

# 检查依赖
check_dependencies() {
    print_info "检查系统依赖..."

    # 检查Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 未安装，请先安装Python 3.8+"
        exit 1
    fi

    # 检查uvicorn
    if ! python3 -c "import uvicorn" 2>/dev/null; then
        print_warning "正在安装uvicorn..."
        pip3 install uvicorn fastapi python-multipart websockets sqlalchemy
    fi

    # 检查端口
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_error "端口8000已被占用，请先关闭相关服务"
        exit 1
    fi

    print_message "依赖检查完成"
}

# 创建工作目录
create_workspace() {
    print_info "创建工作目录..."

    mkdir -p ../workspaces
    mkdir -p ../uploads

    print_message "工作目录创建完成"
}

# 启动服务
start_server() {
    print_info "启动Fix Agent Web服务器..."

    echo ""
    print_message "🚀 服务器启动中..."
    echo -e "${CYAN}   本地访问: http://localhost:8000${NC}"
    echo -e "${CYAN}   API文档: http://localhost:8000/docs${NC}"
    echo ""
    print_info "按 Ctrl+C 停止服务器"
    echo ""

    # 启动服务器
    python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
}

# 主函数
main() {
    print_header

    # 进入backend目录
    cd "$(dirname "$0")/backend" || {
        print_error "无法找到backend目录"
        exit 1
    }

    check_dependencies
    create_workspace
    start_server
}

# 处理中断信号
trap 'print_info "正在关闭服务器..."; exit 0' INT TERM

# 运行主函数
main "$@"