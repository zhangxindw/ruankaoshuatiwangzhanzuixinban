#!/bin/bash
echo "开始部署 ABC 刷题系统..."
set -e

# 克隆项目到临时目录
TEMP_DIR="/opt/abc-new"
APP_DIR="/opt/abc"

# 更新系统
apt-get update
apt-get install -y python3 python3-pip python3-venv nginx git curl

# 克隆到临时目录
cd /opt
rm -rf abc-new
git clone https://github.com/zhangxindw/ruankaoshuatixitong.git abc-new

# 如果原目录存在，只更新代码
if [ -d "$APP_DIR" ]; then
    echo "检测到已存在部署，正在更新代码..."
    # 备份数据库和上传文件
    if [ -f "$APP_DIR/backend/instance/quiz_system.db" ]; then
        cp "$APP_DIR/backend/instance/quiz_system.db" "$TEMP_DIR/backend/instance/quiz_system.db"
    fi
    if [ -d "$APP_DIR/uploads" ]; then
        cp -r "$APP_DIR/uploads" "$TEMP_DIR/"
    fi
    # 备份nginx配置
    if [ -f "/etc/nginx/sites-enabled/abc" ]; then
        cp "/etc/nginx/sites-enabled/abc" "$TEMP_DIR/nginx-abc"
    fi
    # 移除旧目录
    rm -rf $APP_DIR
fi

# 重命名临时目录为正式目录
mv $TEMP_DIR $APP_DIR
cd $APP_DIR

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装后端依赖
cd backend
pip install flask flask-sqlalchemy flask-cors

# 创建数据库（如果不存在）
python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
" 2>/dev/null || true

# 创建uploads目录
mkdir -p uploads
chmod -R 755 uploads

# 配置Nginx
cat > /etc/nginx/sites-available/abc << 'NGINX_EOF'
server {
    listen 80;
    server_name _;

    location /api {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        root /opt/abc/frontend/dist;
        try_files $uri $uri/ /index.html;
        expires -1;
    }

    location /uploads {
        alias /opt/abc/uploads;
        expires 30d;
    }
}
NGINX_EOF

# 启用站点
ln -sf /etc/nginx/sites-available/abc /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && nginx -s reload

# 配置Systemd服务
cat > /etc/systemd/system/abc-backend.service << 'SYSTEMD_EOF'
[Unit]
Description=ABC Quiz System Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/abc/backend
ExecStart=/opt/abc/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
SYSTEMD_EOF

# 停止旧服务并启动新服务
systemctl stop abc-backend 2>/dev/null || true
systemctl daemon-reload
systemctl start abc-backend
systemctl enable abc-backend

# 启动前端
cd /opt/abc/frontend
nohup npm run dev -- --host > /var/log/abc-frontend.log 2>&1 &

echo "部署完成！"
echo "后端服务: http://localhost:5000"
echo "前端服务: http://localhost:3000"
echo "请访问 http://服务器IP 开始使用"
