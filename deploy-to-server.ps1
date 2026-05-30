$ErrorActionPreference = 'Stop'
$server = "154.201.94.140"
$port = 22
$user = "root"
$pass = "6dwic8N532a7"
$repo = "https://github.com/zhangxindw/ruankaoshuatixitong.git"
$appDir = "/var/www/quiz-system"

# Install sshpass if not available
$sshpassPath = "C:\sshpass\sshpass.exe"
if (!(Test-Path $sshpassPath)) {
    Write-Host "Installing sshpass..."
    New-Item -ItemType Directory -Force -Path "C:\sshpass" | Out-Null
    Invoke-WebRequest -Uri "https://github.com/mdrightmire/sshpass/releases/download/v1.0.0/sshpass.exe" -OutFile $sshpassPath -UseBasicParsing
}

# Stop existing services
Write-Host "Stopping existing services..."
& $sshpassPath -p $pass ssh -o StrictHostKeyChecking=no -p $port $user@$server "pkill -f 'node.*vite' 2>/dev/null; pkill -f 'node.*npm' 2>/dev/null; pkill -f 'python.*app.py' 2>/dev/null; pkill -f 'flask' 2>/dev/null; sleep 2"

# Remove old deployment
Write-Host "Removing old deployment..."
& $sshpassPath -p $pass ssh -o StrictHostKeyChecking=no -p $port $user@$server "rm -rf $appDir 2>/dev/null; mkdir -p $appDir; ls -la $appDir"

# Clone repository
Write-Host "Cloning repository..."
& $sshpassPath -p $pass ssh -o StrictHostKeyChecking=no -p $port $user@$server "cd $appDir && git clone $repo . && git checkout main"

# Install backend dependencies
Write-Host "Installing backend dependencies..."
& $sshpassPath -p $pass ssh -o StrictHostKeyChecking=no -p $port $user@$server "cd $appDir/backend && pip install flask flask-sqlalchemy flask-cors"

# Install frontend dependencies
Write-Host "Installing frontend dependencies..."
& $sshpassPath -p $pass ssh -o StrictHostKeyChecking=no -p $port $user@$server "cd $appDir/frontend && npm install && npm run build"

# Start backend
Write-Host "Starting backend..."
& $sshpassPath -p $pass ssh -o StrictHostKeyChecking=no -p $port $user@$server "cd $appDir/backend && nohup python app.py > /var/log/quiz-backend.log 2>&1 &"
& $sshpassPath -p $pass ssh -o StrictHostKeyChecking=no -p $port $user@$server "sleep 2 && curl -s http://localhost:5000/api/chapters | head -c 100"

# Start frontend
Write-Host "Starting frontend..."
& $sshpassPath -p $pass ssh -o StrictHostKeyChecking=no -p $port $user@$server "cd $appDir/frontend && nohup npm run dev -- --host > /var/log/quiz-frontend.log 2>&1 &"

Write-Host "Deployment complete!"
& $sshpassPath -p $pass ssh -o StrictHostKeyChecking=no -p $port $user@$server "ps aux | grep -E 'node|python' | grep -v grep"
