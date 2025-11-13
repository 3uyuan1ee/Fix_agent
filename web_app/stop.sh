#!/bin/bash

# Fix Agent Web 应用停止脚本

echo "🛑 停止 Fix Agent Web 应用..."

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 停止所有相关进程
PIDS=$(pgrep -f "uvicorn main:app" 2>/dev/null)

if [ -n "$PIDS" ]; then
    echo -e "${YELLOW}⏹️  正在停止服务进程...${NC}"
    echo "$PIDS" | xargs kill 2>/dev/null

    # 等待进程结束
    sleep 2

    # 强制停止仍在运行的进程
    REMAINING=$(pgrep -f "uvicorn main:app" 2>/dev/null)
    if [ -n "$REMAINING" ]; then
        echo -e "${YELLOW}⚡ 强制停止剩余进程...${NC}"
        echo "$REMAINING" | xargs kill -9 2>/dev/null
    fi

    echo -e "${GREEN}✅ 服务已停止${NC}"
else
    echo -e "${YELLOW}⚠️  未找到运行中的服务${NC}"
fi

# 清理日志文件（可选）
if [ -f "server.log" ]; then
    echo ""
    read -p "是否删除日志文件 server.log? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm server.log
        echo -e "${GREEN}🗑️  日志文件已删除${NC}"
    fi
fi

echo ""
echo -e "${GREEN}🎉 停止完成！${NC}"
echo -e "${BLUE}💡 重新启动: ./run.sh${NC}"