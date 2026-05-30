#!/bin/bash
SERVER="154.201.94.140"
PORT="22"
USER="root"
PASS="6dwic8N532a7"
REPO="https://github.com/zhangxindw/ruankaoshuatixitong.git"
APP_DIR="/var/www/quiz-system"

export SSHPASS="$PASS"

echo "Stopping existing services..."
sshpass -e ssh -o StrictHostKeyChecking=no -p $PORT $USER@$SERVER "pkill -f 'node.*vite' 2>/dev/null; pkill -f 'node.*npm' 2>/dev/null; pkill -f 'python.*app.py' 2>/dev/null; pkill -f 'flask' 2>/dev/null; sleep 2"

echo "Removing old deployment..."
sshpass -e ssh -o StrictHostKeyChecking=no -p $PORT $USER@$SERVER "rm -rf $APP_DIR 2>/dev/null; mkdir -p $APP_DIR"

echo "Cloning repository..."
sshpass -e ssh -o StrictHostKeyChecking=no -p $PORT $USER@$SERVER "cd $APP_DIR && git clone $REPO . && git checkout main"

echo "Installing backend dependencies..."
sshpass -e ssh -o StrictHostKeyChecking=no -p $PORT $USER@$SERVER "cd $APP_DIR/backend && pip install flask flask-sqlalchemy flask-cors"

echo "Installing frontend dependencies and building..."
sshpass -e ssh -o StrictHostKeyChecking=no -p $PORT $USER@$SERVER "cd $APP_DIR/frontend && npm install && npm run build"

echo "Starting backend..."
sshpass -e ssh -o StrictHostKeyChecking=no -p $PORT $USER@$SERVER "cd $APP_DIR/backend && nohup python app.py > /var/log/quiz-backend.log 2>&1 &"

echo "Starting frontend..."
sshpass -e ssh -o StrictHostKeyChecking=no -p $PORT $USER@$SERVER "cd $APP_DIR/frontend && nohup npm run dev -- --host > /var/log/quiz-frontend.log 2>&1 &"

sleep 3

echo "Checking services..."
sshpass -e ssh -o StrictHostKeyChecking=no -p $PORT $USER@$SERVER "ps aux | grep -E 'node|python' | grep -v grep"
