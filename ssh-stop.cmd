@echo off
echo 6dwic8N532a7 | C:\Windows\System32\OpenSSH\ssh.exe -o StrictHostKeyChecking=no -p 22 root@154.201.94.140 "pkill -f 'node.*vite' 2>/dev/null; pkill -f 'node.*npm' 2>/dev/null; pkill -f 'python.*app.py' 2>/dev/null; pkill -f 'flask' 2>/dev/null; sleep 1; echo 'Services stopped'; ls -la /var/www/"
