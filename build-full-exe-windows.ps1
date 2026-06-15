$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw 'Python was not found. Install Python 3 first, then run this build script again.'
}

if (-not (Test-Path -LiteralPath '.venv')) {
  python -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip pyinstaller

$payloadFiles = @(
  'compose.yaml',
  '.env.example',
  'README.md',
  'README.en.md',
  'LICENSE',
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

$addData = @()
foreach ($file in $payloadFiles) {
  if (-not (Test-Path -LiteralPath $file)) {
    throw "Missing payload file: $file"
  }
  $addData += @('--add-data', "$file;zabbix_payload")
}

& .\.venv\Scripts\python.exe -m PyInstaller `
  --onefile `
  --console `
  --name ZabbixOneClickFull `
  @addData `
  .\zabbix_full_launcher.py

Copy-Item -LiteralPath '.\dist\ZabbixOneClickFull.exe' -Destination '.\ZabbixOneClickFull.exe' -Force

$releaseRoot = Join-Path $PSScriptRoot 'release'
if (-not (Test-Path -LiteralPath $releaseRoot)) {
  New-Item -ItemType Directory -Path $releaseRoot | Out-Null
}
Copy-Item -LiteralPath '.\ZabbixOneClickFull.exe' -Destination (Join-Path $releaseRoot 'ZabbixOneClickFull.exe') -Force

Write-Host ''
Write-Host 'Full single-file EXE built successfully:'
Write-Host (Resolve-Path '.\ZabbixOneClickFull.exe')
Write-Host (Resolve-Path '.\release\ZabbixOneClickFull.exe')
