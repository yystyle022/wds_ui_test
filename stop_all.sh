#!/bin/bash

# 前后端一起停止脚本

if [ -f backend/server.pid ]; then
    PID=$(cat backend/server.pid)
    echo "停止后端 (PID: $PID)..."
    kill $PID
    rm backend/server.pid
else
    echo "未找到 backend/server.pid，尝试查找后端进程..."
    pkill -f "python app.py"
fi

if [ -f frontend/frontend.pid ]; then
    PID=$(cat frontend/frontend.pid)
    echo "停止前端 (PID: $PID)..."
    kill $PID
    rm frontend/frontend.pid
else
    echo "未找到 frontend/frontend.pid，尝试查找前端进程..."
    pkill -f "vite"
fi

echo "前后端均已停止"
