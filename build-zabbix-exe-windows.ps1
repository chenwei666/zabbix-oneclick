$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw 'Python was not found. Install Python 3 first, then run this build script again.'
}

if (-not (Test-Path -LiteralPath '.venv')) {
  python -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip pyinstaller
& .\.venv\Scripts\python.exe -m PyInstaller --onefile --console --name ZabbixOneClick .\zabbix_launcher.py
Copy-Item -LiteralPath '.\dist\ZabbixOneClick.exe' -Destination '.\ZabbixOneClick.exe' -Force

Write-Host ''
Write-Host 'EXE built successfully:'
Write-Host (Resolve-Path '.\ZabbixOneClick.exe')

if (Test-Path -LiteralPath '.\package-zabbix-windows.ps1') {
  PowerShell -NoProfile -ExecutionPolicy Bypass -File .\package-zabbix-windows.ps1
}
