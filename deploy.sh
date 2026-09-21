#!/bin/bash

# 部署脚本

echo "================================"
echo "开始部署项目"
echo "================================"

# 步骤1: 安装前端依赖
echo ""
echo "步骤1: 安装前端依赖..."
cd frontend
npm install

# 步骤2: 构建前端
echo ""
echo "步骤2: 构建前端..."
npm run build

# 步骤3: 返回根目录并创建虚拟环境
cd ..

echo ""
echo "步骤3: 创建Python虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "虚拟环境创建成功"
else
    echo "虚拟环境已存在"
fi

# 步骤4: 激活虚拟环境并安装后端依赖
echo ""
echo "步骤4: 安装后端依赖..."
source venv/bin/activate
pip install -r requirements.txt

# 步骤5: 安装Playwright浏览器（如果需要）
echo ""
echo "步骤5: 安装Playwright浏览器..."
playwright install

echo ""
echo "================================"
echo "部署完成！"
echo "================================"
