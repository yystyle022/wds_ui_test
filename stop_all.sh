#!/bin/bash

# 停止脚本（对应 start_all_background.sh：只有后端一个后台进程）

if [ -f backend/server.pid ]; then
    PID=$(cat backend/server.pid)
    echo "停止后端 (PID: $PID)..."
    kill $PID
    rm backend/server.pid
else
    echo "未找到 backend/server.pid，尝试查找后端进程..."
    pkill -f "python app.py"
fi

echo "已停止"

