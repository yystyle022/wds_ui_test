#!/bin/bash

# 前后端一键后台启动脚本（生产模式：构建前端静态文件，后端统一对外提供服务）

# ---------- 前端构建 ----------
echo "构建前端静态文件..."
cd frontend
npm install
npm run build
cd ..

# ---------- 后端 ----------
echo "在8081端口后台启动后端..."

if [ -d "venv" ]; then
    source venv/bin/activate
fi

cd backend
export PORT=8081
nohup python app.py > server.log 2>&1 &
echo $! > server.pid
echo "后端已启动，PID: $(cat server.pid)，日志: backend/server.log"
cd ..

echo ""
echo "启动完成，访问 http://<服务器IP>:8081 查看完整前后端页面。"

