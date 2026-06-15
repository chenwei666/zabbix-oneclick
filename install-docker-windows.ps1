$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Test-Admin {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = [Security.Principal.WindowsPrincipal]::new($identity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Wait-Docker {
  param([int]$Seconds = 180)

  $deadline = (Get-Date).AddSeconds($Seconds)
  do {
    docker info *> $null
    if ($LASTEXITCODE -eq 0) {
      return $true
    }
    Start-Sleep -Seconds 5
  } while ((Get-Date) -lt $deadline)

  return $false
}

function Install-DockerDesktop {
  Write-Host ''
  Write-Host '[Docker] Installing Docker Desktop for Windows 10/11'
  Write-Host ''

  $docker = Get-Command docker -ErrorAction SilentlyContinue
  if ($docker) {
    docker info *> $null
    $infoOk = ($LASTEXITCODE -eq 0)
    docker compose version *> $null
    $composeOk = ($LASTEXITCODE -eq 0)
    if ($infoOk -and $composeOk) {
      Write-Host 'Docker Desktop is already installed and running.'
      return
    }
  }

  $winget = Get-Command winget -ErrorAction SilentlyContinue
  if ($winget) {
    winget install --id Docker.DockerDesktop --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
      throw 'winget failed to install Docker Desktop.'
    }
  } else {
    $installer = Join-Path $env:TEMP 'DockerDesktopInstaller.exe'
    $url = 'https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe'
    Write-Host "Downloading Docker Desktop installer from $url"
    Invoke-WebRequest -Uri $url -OutFile $installer
    Start-Process -FilePath $installer -Wait -ArgumentList 'install', '--user', '--quiet', '--accept-license'
  }

  $desktop = @(
    "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe",
    'C:\Program Files\Docker\Docker\Docker Desktop.exe'
  ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

  if ($desktop) {
    Start-Process -FilePath $desktop -WindowStyle Hidden
    if (Wait-Docker -Seconds 240) {
      Write-Host 'Docker Desktop is running.'
      return
    }
  }

  Write-Host ''
  Write-Host 'Docker Desktop was installed, but it may require sign-in, license acceptance, WSL setup, or a reboot before first use.'
}

function Invoke-WslRoot {
  param([string]$Command)
  wsl -d Ubuntu-24.04 -u root -- bash -lc $Command
}

function Install-WindowsServerDocker {
  Write-Host ''
  Write-Host '[Docker] Windows Server detected'
  Write-Host 'Docker Desktop is not supported on Windows Server. Preparing WSL2 + Ubuntu + Docker Engine instead.'
  Write-Host ''

  if (-not (Test-Admin)) {
    throw 'Windows Server Docker bootstrap requires an elevated PowerShell session.'
  }

  wsl -d Ubuntu-24.04 -u root -- bash -lc 'docker info >/dev/null 2>&1 && docker compose version >/dev/null 2>&1' 2>$null
  if ($LASTEXITCODE -eq 0) {
    Write-Host 'Docker Engine inside Ubuntu-24.04 is already installed and running.'
    return
  }

  Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -NoRestart | Out-Null
  Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -NoRestart | Out-Null

  wsl --set-default-version 2
  if ($LASTEXITCODE -ne 0) {
    Write-Host 'WSL may need a reboot before setting version 2 succeeds.'
  }

  $distros = wsl --list --quiet 2>$null
  if ($distros -notcontains 'Ubuntu-24.04') {
    Write-Host 'Installing Ubuntu-24.04 for WSL. A reboot may be required if WSL was just enabled.'
    wsl --install -d Ubuntu-24.04 --no-launch
    if ($LASTEXITCODE -ne 0) {
      throw 'Ubuntu-24.04 installation did not complete. Reboot Windows Server and run this installer again.'
    }
  }

  $bootstrap = @'
set -Eeuo pipefail
if ! command -v curl >/dev/null 2>&1; then
  apt-get update
  apt-get install -y ca-certificates curl
fi
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
  sh /tmp/get-docker.sh
fi
if command -v systemctl >/dev/null 2>&1; then
  systemctl enable --now docker || true
else
  service docker start || true
fi
docker --version
docker compose version
'@

  Invoke-WslRoot -Command $bootstrap
  if ($LASTEXITCODE -ne 0) {
    throw 'Docker Engine installation inside Ubuntu-24.04 failed.'
  }

  $bat = @"
@echo off
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0zabbix-windows.ps1" -Action Start
pause
"@
  Set-Content -LiteralPath '.\start-zabbix-windows-server-wsl.bat' -Value $bat -Encoding ASCII

  Write-Host ''
  Write-Host 'Windows Server WSL Docker is ready.'
  Write-Host 'Use start-zabbix-windows-server-wsl.bat to start Zabbix through WSL.'
}

$os = Get-CimInstance Win32_OperatingSystem
if ($os.ProductType -ne 1) {
  Install-WindowsServerDocker
} else {
  Install-DockerDesktop
}
