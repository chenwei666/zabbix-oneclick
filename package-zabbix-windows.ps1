$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$appVersion = '1.0.4'
$exeFile = "ZabbixOneClick-v$appVersion.exe"

$releaseRoot = Join-Path $PSScriptRoot 'release'
$packageDir = Join-Path $releaseRoot "ZabbixOneClick-v$appVersion"
$zipPath = Join-Path $releaseRoot "ZabbixOneClick-v$appVersion.zip"

if (Test-Path -LiteralPath $packageDir) {
  Remove-Item -LiteralPath $packageDir -Recurse -Force
}
New-Item -ItemType Directory -Path $packageDir | Out-Null

$files = @(
  $exeFile,
  'compose.yaml',
  '.env.example',
  'README.md',
  'README.en.md',
  'LICENSE',
  'zabbix-oneclick.ico',
  'zabbix-windows.ps1',
  'install-docker-windows.ps1',
  'install-docker-windows.bat',
  'start-zabbix-windows.bat',
  'stop-zabbix-windows.bat',
  'restart-zabbix-windows.bat',
  'status-zabbix-windows.bat',
  'health-check-zabbix-windows.bat',
  'configure-zabbix-windows.bat',
  'check-update-zabbix-windows.bat',
  'update-zabbix-windows.bat',
  'repair-zabbix-windows.bat',
  'logs-zabbix-windows.bat',
  'open-zabbix-windows.bat',
  'backup-zabbix-windows.bat',
  'reset-zabbix-data-windows.bat',
  'install-docker-linux.sh',
  'start-zabbix-linux.sh',
  'stop-zabbix-linux.sh',
  'status-zabbix-linux.sh',
  'check-update-zabbix-linux.sh',
  'update-zabbix-linux.sh',
  'zabbix-start.desktop',
  'zabbix-stop.desktop',
  'zabbix-update.desktop'
)

foreach ($file in $files) {
  if (-not (Test-Path -LiteralPath $file)) {
    throw "Missing package file: $file"
  }
  Copy-Item -LiteralPath $file -Destination $packageDir -Force
}

if (Test-Path -LiteralPath $zipPath) {
  Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path (Join-Path $packageDir '*') -DestinationPath $zipPath -Force

Write-Host ''
Write-Host 'Release package created:'
Write-Host $packageDir
Write-Host $zipPath
