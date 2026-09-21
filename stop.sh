#!/bin/bash

# 停止脚本

if [ -f backend/server.pid ]; then
    PID=$(cat backend/server.pid)
    echo "停止服务器 (PID: $PID)..."
    kill $PID
    rm backend/server.pid
    echo "服务器已停止"
else
    echo "未找到server.pid文件，尝试查找Python进程..."
    pkill -f "python3 app.py"
    echo "已尝试停止所有相关进程"
fi
