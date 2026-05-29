# ABC 刷题系统 - 完整部署教程

## 准备工作

### 所需信息
- 服务器IP：154.201.94.140
- SSH端口：22
- 用户名：root
- 密码：6dwic8N532a7

### 前置条件
1. 一台 Linux 服务器（Ubuntu/Debian 推荐）
2. GitHub 仓库已推送：https://github.com/zhangxindw/abcshuatixitong.git
3. 本地电脑可通过 SSH 连接服务器

---

## 步骤 1：连接服务器

### Windows 用户（使用 PowerShell）
```powershell
ssh -p 22 root@154.201.94.140
```

### Windows 用户（使用 PuTTY）
1. 下载并安装 PuTTY
2. Host Name (or IP address): 154.201.94.140
3. Port: 22
4. 点击 Open
5. 输入用户名和密码

### Mac/Linux 用户
```bash
ssh -p 22 root@154.201.94.140
```

---

## 步骤 2：执行一键部署脚本

连接到服务器后，复制以下命令并粘贴到终端：

```bash
# 创建部署脚本
cat > /opt/deploy-server.sh << 'EOF'
#!/bin/bash
echo "开始部署 ABC 刷题系统..."
set -e

# 更新系统
apt-get update
apt-get install -y python3 python3-pip python3-venv nginx git curl nodejs npm

# 克隆项目
cd /opt
if [ -d "abc" ]; then
    rm -rf abc
fi
git clone https://github.com/zhangxindw/abcshuatixitong.git abc
cd abc

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装后端依赖
cd backend
pip install -r requirements.txt

# 创建数据库
python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
"

# 创建uploads目录
mkdir -p uploads

# 配置Nginx
cat > /etc/nginx/sites-available/abc << 'NGINXEOF'
server {
    listen 80;
    server_name _;

    location /api {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        root /opt/abc/frontend/dist;
        try_files \$uri \$uri/ /index.html;
    }
}
NGINXEOF

# 启用站点
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/abc /etc/nginx/sites-enabled/

# 编译前端
cd /opt/abc/frontend
npm install
npm run build

# 创建systemd服务
cat > /etc/systemd/system/abc-backend.service << 'SYSTEMDEOF'
[Unit]
Description=ABC Quiz System Backend
After=network.target

[Service]
User=root
WorkingDirectory=/opt/abc/backend
Environment="PATH=/opt/abc/venv/bin"
ExecStart=/opt/abc/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
SYSTEMDEOF

# 启动服务
systemctl daemon-reload
systemctl enable abc-backend
systemctl start abc-backend
systemctl restart nginx

echo ""
echo "========================================"
echo "✅ 部署完成！"
echo "访问地址: http://154.201.94.140"
echo "========================================"
echo ""
echo "后端服务状态："
systemctl status abc-backend --no-pager
echo ""
echo "Nginx状态："
systemctl status nginx --no-pager
EOF

# 执行部署
chmod +x /opt/deploy-server.sh
/opt/deploy-server.sh
```

---

## 步骤 3：验证部署

部署完成后，你将看到：

```
========================================
✅ 部署完成！
访问地址: http://154.201.94.140
========================================
```

在浏览器中访问：**http://154.201.94.140**

---

## 常用管理命令

### 查看后端服务状态
```bash
systemctl status abc-backend
```

### 重启后端服务
```bash
systemctl restart abc-backend
```

### 查看后端服务日志
```bash
journalctl -u abc-backend -f
```

### 查看Nginx状态
```bash
systemctl status nginx
```

### 重启Nginx
```bash
systemctl restart nginx
```

### 查看Nginx日志
```bash
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

---

## 更新项目

当你更新了 GitHub 仓库后，在服务器上执行：

```bash
cd /opt/abc
git pull

# 更新后端依赖
source venv/bin/activate
cd backend
pip install -r requirements.txt

# 重新编译前端
cd ../frontend
npm install
npm run build

# 重启服务
systemctl restart abc-backend
systemctl restart nginx
```

---

## 项目目录结构

```
/opt/abc/
├── backend/
│   ├── app.py              # 后端主程序
│   ├── models.py           # 数据库模型
│   ├── requirements.txt    # Python依赖
│   ├── instance/
│   │   └── quiz_system.db  # 数据库文件
│   └── uploads/            # 上传文件目录
├── frontend/
│   ├── src/                # 前端源码
│   └── dist/               # 编译后的前端文件
└── venv/                   # Python虚拟环境
```

---

## 故障排查

### 问题：无法访问网站
1. 检查防火墙是否开放 80 端口：
   ```bash
   ufw allow 80
   ```
2. 检查Nginx是否运行：
   ```bash
   systemctl status nginx
   ```

### 问题：API请求失败
1. 检查后端服务：
   ```bash
   systemctl status abc-backend
   ```
2. 查看后端日志：
   ```bash
   journalctl -u abc-backend
   ```

### 问题：502 Bad Gateway
通常是后端服务没有运行，重启后端：
```bash
systemctl restart abc-backend
```

---

## 安全建议

1. **不要在代码中存储密码**
2. **修改默认SSH端口（可选）**
3. **启用防火墙**：
   ```bash
   ufw enable
   ufw allow 22
   ufw allow 80
   ```
4. **定期更新系统**：
   ```bash
   apt-get update && apt-get upgrade
   ```

---

## 支持

如有问题，请检查：
1. GitHub 仓库是否正确
2. 服务器是否有足够的内存（推荐至少1GB）
3. 网络连接是否正常
