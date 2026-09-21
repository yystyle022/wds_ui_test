#!/bin/bash

# 启动脚本

echo "在8081端口启动服务器..."

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
fi

cd backend
export PORT=8081
python app.py
