#!/bin/bash

# Fix Agent Web 完整版停止脚本

echo "🛑 停止 Fix Agent Web 完整版..."

# 停止uvicorn服务
pkill -f "uvicorn main:app" 2>/dev/null

# 停止可能的Python服务
pkill -f "main.py" 2>/dev/null

echo "✅ 服务器已停止"