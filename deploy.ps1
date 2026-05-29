# ABC 刷题系统 - 直接部署脚本
# 请确保已安装 OpenSSH 客户端 (Windows 10/11 默认已安装)

$serverIp = "154.201.94.140"
$serverUser = "root"
$serverPort = "22"
$deployScriptPath = "deploy-server.sh"

# 上传部署脚本到服务器
Write-Host "正在上传部署脚本到服务器..."
scp -P $serverPort $deployScriptPath ${serverUser}@${serverIp}:/opt/

# 在服务器上执行部署脚本
Write-Host "正在服务器上执行部署..."
ssh -p $serverPort ${serverUser}@${serverIp} "chmod +x /opt/deploy-server.sh && /opt/deploy-server.sh"

Write-Host "部署完成！"
Write-Host "访问地址: http://${serverIp}"
