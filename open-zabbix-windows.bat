@echo off
setlocal EnableExtensions
cd /d "%~dp0"

PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0zabbix-windows.ps1" -Action Open
if errorlevel 1 exit /b %errorlevel%
pause
