# 云服务器部署指南

本指南假设云服务器为 **Ubuntu 20.04/22.04**，已有 SSH 登录权限。以下命令需要在服务器终端（通过 SSH 登录后）执行。

## 1. 安装系统依赖

```bash
sudo apt update
sudo apt install -y git nginx curl software-properties-common

# 本项目的 requirements.txt 里锁定了大量旧版本包（numpy/pandas/pydantic/gevent 等），
# 是从 Python 3.10 环境冻结出来的。Ubuntu 22.04+ 自带的 python3 可能是 3.11/3.12，
# 直接用会导致多个包源码编译失败甚至编译成功但行为不兼容。
# 因此这里额外安装 Python 3.10，专门给该项目使用。
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev

# 安装 Node.js 18.x
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

> 如果你的服务器已经有 Python 3.10/3.11，可以跳过 deadsnakes 步骤，直接用系统自带的 3.10/3.11 创建虚拟环境。**不建议用 3.12+**，本项目依赖版本没有跟进适配。

## 2. 拉取项目代码

```bash
sudo mkdir -p /opt/wds_ui_test
sudo chown $USER:$USER /opt/wds_ui_test
git clone https://github.com/yystyle022/wds_ui_test.git /opt/wds_ui_test
cd /opt/wds_ui_test
```

## 3. 安装后端依赖

```bash
cd /opt/wds_ui_test
python3.10 -m venv venv
source venv/bin/activate

pip install --upgrade pip setuptools wheel
pip install --prefer-binary -r requirements.txt

# 安装 Playwright 浏览器及系统依赖（headless 自动化必需）
playwright install --with-deps chromium
```

> 如果之前已经用系统默认 Python（3.12）创建过 `venv` 目录，先删除重建：
> `rm -rf venv && python3.10 -m venv venv`

## 4. 构建前端

```bash
cd /opt/wds_ui_test/frontend
npm install
npm run build
# 产物在 frontend/dist，Flask 会直接把它当静态文件托管
```

## 5. 验证能否手动运行

```bash
cd /opt/wds_ui_test
source venv/bin/activate
cd backend
PORT=8081 python app.py
```

浏览器访问 `http://<服务器公网IP>:8081`，确认页面能正常打开后，按 `Ctrl+C` 停止，转为用 systemd 常驻运行。

## 6. 用 systemd 常驻运行（进程守护，断线不掉）

```bash
sudo cp /opt/wds_ui_test/deploy/wds-backend.service /etc/systemd/system/wds-backend.service
sudo systemctl daemon-reload
sudo systemctl enable wds-backend
sudo systemctl start wds-backend

# 查看状态 / 日志
sudo systemctl status wds-backend
sudo journalctl -u wds-backend -f
```

> `deploy/wds-backend.service` 默认用 `www-data` 用户运行，工作目录为 `/opt/wds_ui_test`。如果克隆路径或用户不同，先编辑该文件里的 `User`、`WorkingDirectory`、`ExecStart` 再复制。

## 7. （可选）用 Nginx 反向代理到 80 端口

```bash
sudo cp /opt/wds_ui_test/deploy/nginx.conf /etc/nginx/sites-available/wds_ui_test
sudo ln -s /etc/nginx/sites-available/wds_ui_test /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

编辑 `/etc/nginx/sites-available/wds_ui_test` 里的 `server_name` 为你的域名或公网 IP。

之后即可通过 `http://<域名或IP>` 直接访问（无需带 8081 端口）。

## 8. （可选）HTTPS 证书

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your_domain.com
```

## 9. 防火墙放行端口

```bash
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8081   # 若不走 Nginx，直接暴露后端端口时才需要
sudo ufw enable
```

## 10. 后续更新代码

```bash
cd /opt/wds_ui_test
git pull
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install --prefer-binary -r requirements.txt
cd frontend && npm install && npm run build
sudo systemctl restart wds-backend
```

## 常见问题

- **Playwright 报浏览器缺失**：重新执行 `playwright install --with-deps chromium`。
- **端口被占用**：`sudo lsof -i :8081` 查看占用进程，或修改 `wds-backend.service` 里的 `PORT` 环境变量。
- **静态资源 404**：确认执行过 `npm run build`，且 `frontend/dist` 目录存在。
- **`pip install` 报 `distutils`/`pkgutil.ImpImporter`/Cython 编译等错误**：说明用的是 Python 3.12（或更新版本）创建的虚拟环境，与 `requirements.txt` 里锁定的旧版本包不兼容。删除 `venv` 后用 `python3.10 -m venv venv` 重新创建，参考第 3 步。
- **截图/日志目录权限问题**：确保 systemd 里配置的 `User`（如 `www-data`）对 `backend/screenshots` 等目录有写权限：
  ```bash
  sudo chown -R www-data:www-data /opt/wds_ui_test/backend
  ```
