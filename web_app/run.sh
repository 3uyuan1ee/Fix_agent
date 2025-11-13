#!/bin/bash

# Fix Agent Web 应用启动脚本
# 简化版 - 专注于最佳用户体验

echo "🚀 Fix Agent Web 应用启动中..."
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 未安装，请先安装Python3${NC}"
    exit 1
fi

# 检查当前目录
if [ ! -f "backend/main.py" ]; then
    echo -e "${RED}❌ 请在 web_app 目录下运行此脚本${NC}"
    echo "正确用法: cd web_app && ./run.sh"
    exit 1
fi

echo -e "${BLUE}📁 当前目录: $(pwd)${NC}"
echo -e "${BLUE}🐍 Python版本: $(python3 --version)${NC}"
echo ""

# 检查服务是否已运行
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  服务已在运行中${NC}"
    echo -e "${GREEN}🌐 请在浏览器中打开: http://localhost:8000${NC}"
    echo ""
    echo -e "${BLUE}💡 如需重启服务，请先运行:${NC}"
    echo "   ./stop.sh"
    echo ""
    exit 0
fi

# 安装依赖（如果需要）
echo -e "${BLUE}📦 检查依赖...${NC}"
cd backend
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}⬇️  安装Python依赖...${NC}"
    pip3 install -r requirements.txt > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 依赖安装完成${NC}"
    else
        echo -e "${RED}❌ 依赖安装失败${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ 依赖已就绪${NC}"
fi

# 启动服务
echo ""
echo -e "${BLUE}🔧 启动Web服务器...${NC}"
echo -e "${YELLOW}   服务地址: http://localhost:8000${NC}"
echo -e "${YELLOW}   API文档:  http://localhost:8000/docs${NC}"
echo ""

# 在后台启动服务器
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 > ../server.log 2>&1 &
SERVER_PID=$!

# 等待服务启动
echo -e "${BLUE}⏳ 等待服务启动...${NC}"
for i in {1..15}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 服务启动成功！${NC}"
        echo ""
        echo -e "${GREEN}🎉 Fix Agent Web 应用已准备就绪！${NC}"
        echo ""
        echo -e "${BLUE}📱 访问地址:${NC}"
        echo -e "   ${GREEN}http://localhost:8000${NC} - 主界面"
        echo -e "   ${GREEN}http://localhost:8000/docs${NC} - API文档"
        echo ""
        echo -e "${BLUE}💡 使用说明:${NC}"
        echo "   • 在浏览器中打开上述地址"
        echo "   • 开始与AI助手对话"
        echo "   • 支持代码分析、缺陷修复等功能"
        echo ""
        echo -e "${BLUE}🛑 停止服务: ./stop.sh${NC}"
        echo ""
        echo -e "${YELLOW}📝 服务日志: ./server.log${NC}"
        echo ""

        # 尝试自动打开浏览器
        if command -v open &> /dev/null; then
            echo -e "${BLUE}🌐 正在自动打开浏览器...${NC}"
            sleep 2
            open http://localhost:8000
        fi

        exit 0
    fi

    if [ $i -eq 15 ]; then
        echo -e "${RED}❌ 服务启动失败${NC}"
        echo -e "${YELLOW}💡 请检查日志: ./server.log${NC}"
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi

    sleep 1
    echo -n "."
done

cd ..