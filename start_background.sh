#!/bin/bash

# 后台启动脚本

echo "在8081端口后台启动服务器..."

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
fi

cd backend
export PORT=8081
nohup python app.py > server.log 2>&1 &
echo $! > server.pid
echo "服务器已启动，PID: $(cat server.pid)"
echo "日志文件: backend/server.log"
