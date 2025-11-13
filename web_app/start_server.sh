#!/bin/bash

# Fix Agent Web 完整版启动脚本

echo "🚀 启动 Fix Agent Web 完整版..."
echo "================================================"

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python3"
    exit 1
fi

# 检查是否在正确的目录
if [ ! -f "backend/main.py" ]; then
    echo "❌ 请在web_app目录下运行此脚本"
    exit 1
fi

# 检查后端是否已启动
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 后端服务已启动"
else
    echo "🔧 启动后端服务..."
    cd backend
    python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    cd ..

    # 等待服务启动
    echo "⏳ 等待后端服务启动..."
    for i in {1..15}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo "✅ 后端服务启动成功"
            break
        fi
        if [ $i -eq 15 ]; then
            echo "❌ 后端服务启动失败"
            kill $BACKEND_PID 2>/dev/null
            exit 1
        fi
        sleep 1
    done
fi

# 运行完整测试
echo "🧪 运行完整功能测试..."
python test_complete.py

echo ""
echo "================================================"
echo "🎉 Fix Agent Web 完整版已启动成功！"
echo ""
echo "🔗 可用服务:"
echo "   📡 API服务: http://localhost:8000"
echo "   📚 API文档: http://localhost:8000/docs"
echo "   🏥 健康检查: http://localhost:8000/health"
echo ""
echo "✨ 核心功能:"
echo "   ✅ RESTful API (会话管理、文件上传等)"
echo "   ✅ WebSocket流式通信"
echo "   ✅ AI适配器 (支持CLI集成)"
echo "   ✅ 数据库持久化"
echo "   ✅ 记忆系统"
echo ""
echo "🛑 停止服务: 按 Ctrl+C 或运行 ./stop_server.sh"
echo "================================================"

# 保持脚本运行，等待用户中断
echo "按 Ctrl+C 停止服务器..."
trap 'echo ""; echo "🛑 正在停止服务..."; pkill -f "uvicorn main:app" 2>/dev/null; echo "✅ 服务已停止"; exit 0' INT

while true; do
    sleep 1
done