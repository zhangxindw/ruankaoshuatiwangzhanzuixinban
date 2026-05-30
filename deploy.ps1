# ABC 刷题系统 - 直接部署脚本
# 请设置环境变量或直接修改下方变量值

$serverIp = $env:SERVER_IP
$serverUser = $env:SERVER_USER
$serverPass = $env:SERVER_PASS
$serverPort = if ($env:SERVER_PORT) { $env:SERVER_PORT } else { "22" }
$deployScriptPath = "deploy-server.sh"

if (-not $serverIp -or -not $serverUser -or -not $serverPass) {
    Write-Host "错误: 请设置环境变量 SERVER_IP, SERVER_USER, SERVER_PASS"
    Write-Host "示例: $env:SERVER_IP='154.201.94.140'"
    exit 1
}

Write-Host "正在上传部署脚本到服务器..."
& scp -P $serverPort $deployScriptPath ${serverUser}@${serverIp}:/opt/

Write-Host "正在服务器上执行部署..."
& ssh -p $serverPort ${serverUser}@${serverIp} "chmod +x /opt/deploy-server.sh && /opt/deploy-server.sh"

Write-Host "部署完成！"
Write-Host "访问地址: http://${serverIp}"
