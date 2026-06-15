@echo off
setlocal EnableExtensions
cd /d "%~dp0"

PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-docker-windows.ps1"
if errorlevel 1 exit /b %errorlevel%
pause
