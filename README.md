# Flask + Vue3 Web Automation Testing Platform

一个基于 Flask 后端和 Vue3 前端的 Web 自动化测试平台，使用 Playwright 进行浏览器自动化，支持测试用例管理、元素定位、变量管理和测试执行等功能。

详细架构说明见 [项目架构文档.md](项目架构文档.md)，变量作用域模型见 [变量管理功能说明.md](变量管理功能说明.md)。

## 功能特性

- 测试用例管理：创建、编辑、删除、拖拽排序和执行测试用例
- 元素库管理：支持 XPath 和 CSS 两种定位方式
- 变量管理：固定值、数据库、随机数和授权码等多种变量类型
- 环境配置：支持多环境管理（开发、测试、生产等）
- 数据库集成：支持 MySQL 和 PostgreSQL 数据库变量查询
- 执行报告：详细的测试执行报告和截图记录

## 技术栈

- 后端：Flask + Playwright，JSON 文件持久化（无 ORM），Python 3.10+
- 前端：Vue 3 + Naive UI + Vite + TypeScript/JavaScript

## 项目结构

```
flask_vue/
├── backend/
│   ├── app.py                 # Flask 主应用
│   ├── test_executor.py       # Playwright 测试执行器
│   ├── data.json / elements.json / variables.json / ...  # JSON 数据存储
│   └── requirements.txt       # Python 依赖（位于仓库根目录）
├── frontend/
│   ├── src/                   # Vue 组件、路由、composables
│   ├── package.json
│   └── vite.config.js
├── start.sh / start_background.sh / stop.sh / deploy.sh
└── requirements.txt
```

## 快速开始

### 前置条件

- Python 3.10+
- Node.js 16+

### 后端

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r ../requirements.txt
playwright install
python app.py   # 默认监听 8081 端口
```

### 前端

```bash
cd frontend
npm install
npm run dev     # 默认监听 5173 端口，代理 /api 到 8081
```

访问 http://localhost:5173

### 生产部署

```bash
./deploy.sh
```

停止服务：`./stop.sh`

## 变量引用语法

在测试步骤中引用变量：`${varName}` 或 `{{varName}}`

## 许可证

MIT License
