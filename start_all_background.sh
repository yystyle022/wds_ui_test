#!/bin/bash

# 前后端一起后台启动脚本

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

# ---------- 前端 ----------
echo "在5173端口后台启动前端（开发模式，代理 /api 到 8081）..."

cd frontend
nohup npm run dev > frontend.log 2>&1 &
echo $! > frontend.pid
echo "前端已启动，PID: $(cat frontend.pid)，日志: frontend/frontend.log"
cd ..

echo ""
echo "前后端均已后台启动完成。"
