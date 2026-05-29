#!/bin/bash
echo "开始部署 ABC 刷题系统..."
set -e

# 更新系统
apt-get update
apt-get install -y python3 python3-pip python3-venv nginx git curl

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
cat > /etc/nginx/sites-available/abc << 'EOF'
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
EOF

# 启用站点
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/abc /etc/nginx/sites-enabled/

# 编译前端
cd /opt/abc/frontend
npm install
npm run build

# 创建systemd服务
cat > /etc/systemd/system/abc-backend.service << 'EOF'
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
EOF

# 启动服务
systemctl daemon-reload
systemctl enable abc-backend
systemctl start abc-backend
systemctl restart nginx

echo "部署完成！"
echo "后端服务状态："
systemctl status abc-backend --no-pager
echo "Nginx状态："
systemctl status nginx --no-pager
