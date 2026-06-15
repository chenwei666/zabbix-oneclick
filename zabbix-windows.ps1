param(
  [ValidateSet('Start', 'Stop', 'Restart', 'Status', 'Logs', 'Open', 'CheckUpdate', 'Update', 'Configure', 'HealthCheck', 'Repair', 'Backup', 'ResetData')]
  [string]$Action = 'Start',
  [switch]$OpenBrowser
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Write-Title {
  param([string]$Text)
  Write-Host ''
  Write-Host "[Zabbix] $Text"
  Write-Host ''
}

function Get-EnvValue {
  param(
    [string]$Name,
    [string]$DefaultValue = ''
  )

  if (-not (Test-Path -LiteralPath '.env')) {
    return $DefaultValue
  }

  $line = Get-Content -LiteralPath '.env' | Where-Object { $_ -match "^\s*$([regex]::Escape($Name))=" } | Select-Object -Last 1
  if (-not $line) {
    return $DefaultValue
  }

  return ($line -split '=', 2)[1].Trim()
}

function Ensure-EnvFile {
  if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
    Write-Host 'Created .env from .env.example.'
  }

  $required = @(
    'ZABBIX_IMAGE_TAG',
    'ZABBIX_WEB_PORT',
    'ZABBIX_SERVER_PORT',
    'MYSQL_ROOT_PASSWORD',
    'MYSQL_DATABASE',
    'MYSQL_USER',
    'MYSQL_PASSWORD',
    'PHP_TZ',
    'ZBX_CACHESIZE',
    'ZBX_TRENDCACHESIZE',
    'ZBX_STARTJAVAPOLLERS',
    'ZBX_STARTREPORTWRITERS'
  )

  $example = @{}
  Get-Content -LiteralPath '.env.example' | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
      $example[$matches[1].Trim()] = $matches[2]
    }
  }

  $envText = if (Test-Path -LiteralPath '.env') { Get-Content -LiteralPath '.env' } else { @() }
  $existing = @{}
  foreach ($line in $envText) {
    if ($line -match '^\s*([^#][^=]+)=') {
      $existing[$matches[1].Trim()] = $true
    }
  }

  $missing = @($required | Where-Object { -not $existing.ContainsKey($_) -and $example.ContainsKey($_) })
  if ($missing.Count -gt 0) {
    Add-Content -LiteralPath '.env' -Value ''
    foreach ($key in $missing) {
      Add-Content -LiteralPath '.env' -Value "$key=$($example[$key])"
    }
    Write-Host "Repaired .env; added missing keys: $($missing -join ', ')"
  }
}

function Set-EnvValue {
  param(
    [string]$Name,
    [string]$Value
  )

  Ensure-EnvFile
  $lines = Get-Content -LiteralPath '.env'
  $found = $false
  $newLines = foreach ($line in $lines) {
    if ($line -match "^\s*$([regex]::Escape($Name))=") {
      $found = $true
      "$Name=$Value"
    } else {
      $line
    }
  }
  if (-not $found) {
    $newLines += "$Name=$Value"
  }
  Set-Content -LiteralPath '.env' -Value $newLines -Encoding ASCII
}

function Test-PortValue {
  param([string]$Value)
  $port = 0
  if (-not [int]::TryParse($Value, [ref]$port) -or $port -lt 1 -or $port -gt 65535) {
    throw "Invalid port: $Value. Use a number from 1 to 65535."
  }
  return $port
}

function Test-PortAvailable {
  param(
    [int]$Port,
    [string]$ServiceName
  )

  $targetPort = if ($ServiceName -eq 'zabbix-web') { 8080 } else { 10051 }
  $published = docker compose port $ServiceName $targetPort 2>$null
  if ($LASTEXITCODE -eq 0 -and $published) {
    $publishedPort = ($published | Select-Object -First 1) -replace '^.*:', ''
    if ($publishedPort -eq [string]$Port) {
      return
    }
  }

  $listeners = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
  if ($listeners) {
    $owners = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
    $details = @()
    foreach ($pid in $owners) {
      $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
      if ($proc) {
        $details += "$($proc.ProcessName)($pid)"
      } else {
        $details += "pid:$pid"
      }
    }
    throw "Port $Port is already in use by $($details -join ', '). Change $ServiceName port in Configure."
  }
}

function Test-ComposeConfig {
  Ensure-EnvFile
  docker compose --env-file .env config --quiet
  if ($LASTEXITCODE -ne 0) {
    throw 'compose.yaml or .env is invalid. Run Configure or Repair.'
  }
}

function Test-PortsBeforeStart {
  $webPort = Test-PortValue (Get-EnvValue -Name 'ZABBIX_WEB_PORT' -DefaultValue '8080')
  $serverPort = Test-PortValue (Get-EnvValue -Name 'ZABBIX_SERVER_PORT' -DefaultValue '10051')
  if ($webPort -eq $serverPort) {
    throw 'ZABBIX_WEB_PORT and ZABBIX_SERVER_PORT cannot use the same port.'
  }
  Test-PortAvailable -Port $webPort -ServiceName 'zabbix-web'
  Test-PortAvailable -Port $serverPort -ServiceName 'zabbix-server'
}

function Ensure-Docker {
  $os = Get-CimInstance Win32_OperatingSystem
  if ($os.ProductType -ne 1) {
    Ensure-WindowsServerDocker
    return 'wsl'
  }

  $docker = Get-Command docker -ErrorAction SilentlyContinue
  if (-not $docker) {
    Write-Host 'Docker was not found. Starting Docker installation...'
    PowerShell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'install-docker-windows.ps1')
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $docker) {
      throw 'Docker installation finished, but docker CLI was not found. Restart this terminal or reboot, then try again.'
    }
  }

  docker info *> $null
  if ($LASTEXITCODE -ne 0) {
    $desktop = @(
      "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe",
      'C:\Program Files\Docker\Docker\Docker Desktop.exe'
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if ($desktop) {
      Write-Host 'Docker is installed but not running. Starting Docker Desktop...'
      Start-Process -FilePath $desktop -WindowStyle Hidden
      $deadline = (Get-Date).AddMinutes(4)
      do {
        docker info *> $null
        if ($LASTEXITCODE -eq 0) {
          break
        }
        Start-Sleep -Seconds 5
      } while ((Get-Date) -lt $deadline)
    }
    if ($LASTEXITCODE -ne 0) {
      throw 'Docker is installed but not running, or the current user cannot access Docker.'
    }
  }

  docker compose version *> $null
  if ($LASTEXITCODE -ne 0) {
    throw 'Docker Compose v2 was not found. Update Docker Desktop or install the Docker Compose plugin.'
  }

  $osType = (docker info --format '{{.OSType}}').Trim()
  if ($osType -ne 'linux') {
    throw "Docker is currently using '$osType' containers. This stack requires Linux containers."
  }

  return 'windows'
}

function Ensure-WindowsServerDocker {
  Write-Host "Windows Server detected. Using WSL2 + Ubuntu + Docker Engine."
  wsl -d Ubuntu-24.04 -u root -- bash -lc 'docker info >/dev/null 2>&1 && docker compose version >/dev/null 2>&1'
  if ($LASTEXITCODE -eq 0) {
    return
  }

  $script = Join-Path $PSScriptRoot 'install-docker-windows.ps1'
  PowerShell -NoProfile -ExecutionPolicy Bypass -File $script
}

function Invoke-WslZabbix {
  param(
    [ValidateSet('start', 'check-update', 'update', 'status', 'stop')]
    [string]$LinuxAction
  )

  $linuxPath = (wsl -d Ubuntu-24.04 -u root -- wslpath -a $PSScriptRoot).Trim()
  if ($LASTEXITCODE -ne 0 -or -not $linuxPath) {
    throw 'Failed to resolve workspace path inside WSL.'
  }

  $command = "cd '$linuxPath' && chmod +x ./*.sh && "
  switch ($LinuxAction) {
    'start' { $command += './start-zabbix-linux.sh' }
    'check-update' { $command += './check-update-zabbix-linux.sh' }
    'update' { $command += './update-zabbix-linux.sh' }
    'status' { $command += './status-zabbix-linux.sh' }
    'stop' { $command += './stop-zabbix-linux.sh' }
  }

  wsl -d Ubuntu-24.04 -u root -- bash -lc $command
  if ($LASTEXITCODE -ne 0) {
    throw "WSL action failed: $LinuxAction"
  }
}

function Wait-ZabbixReady {
  param([int]$Seconds = 180)

  $webPort = Get-EnvValue -Name 'ZABBIX_WEB_PORT' -DefaultValue '8080'
  $deadline = (Get-Date).AddSeconds($Seconds)
  do {
    $serverState = (docker compose ps --status running --services 2>$null)
    $webOk = $false
    try {
      $response = Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:$webPort" -TimeoutSec 5
      $webOk = ($response.StatusCode -eq 200)
    } catch {
      $webOk = $false
    }
    if ($serverState -contains 'zabbix-server' -and $serverState -contains 'zabbix-web' -and $webOk) {
      return $true
    }
    Start-Sleep -Seconds 5
  } while ((Get-Date) -lt $deadline)

  return $false
}

function Invoke-HealthCheck {
  Write-Title 'Health check'
  $mode = Ensure-Docker
  if ($mode -eq 'wsl') {
    Invoke-WslZabbix -LinuxAction status
    return
  }

  Ensure-EnvFile
  Test-ComposeConfig
  docker compose ps

  $webPort = Get-EnvValue -Name 'ZABBIX_WEB_PORT' -DefaultValue '8080'
  Write-Host ''
  Write-Host "Checking Web: http://localhost:$webPort"
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:$webPort" -TimeoutSec 15
    Write-Host "Web status: $($response.StatusCode) $($response.StatusDescription)"
  } catch {
    Write-Host "Web check failed: $($_.Exception.Message)" -ForegroundColor Yellow
  }

  $rootPassword = Get-EnvValue -Name 'MYSQL_ROOT_PASSWORD' -DefaultValue ''
  if ($rootPassword) {
    $query = "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='zabbix'; SELECT COUNT(*) FROM zabbix.users;"
    $db = docker exec -e "MYSQL_PWD=$rootPassword" zabbix-mysql mysql -uroot -N -e $query 2>$null
    if ($LASTEXITCODE -eq 0) {
      $values = @($db | Where-Object { $_ -match '^\d+$' })
      Write-Host "Database tables: $($values[0])"
      Write-Host "Database users: $($values[1])"
      if ([int]$values[0] -lt 100 -or [int]$values[1] -lt 1) {
        Write-Host 'Database looks incomplete. Run Repair.' -ForegroundColor Yellow
      }
    } else {
      Write-Host 'Database check failed. Check MySQL container logs.' -ForegroundColor Yellow
    }
  }

  Write-Host ''
  docker compose logs --tail=30 zabbix-server zabbix-web
}

function Invoke-Configure {
  Write-Title 'Configure'
  Ensure-EnvFile

  Write-Host "1. Web port          : $(Get-EnvValue -Name 'ZABBIX_WEB_PORT' -DefaultValue '8080')"
  Write-Host "2. Server port       : $(Get-EnvValue -Name 'ZABBIX_SERVER_PORT' -DefaultValue '10051')"
  Write-Host "3. Timezone          : $(Get-EnvValue -Name 'PHP_TZ' -DefaultValue 'Asia/Bangkok')"
  Write-Host "4. Zabbix image tag  : $(Get-EnvValue -Name 'ZABBIX_IMAGE_TAG' -DefaultValue 'alpine-7.0-latest')"
  Write-Host "5. MySQL root password"
  Write-Host "6. Zabbix DB password"
  Write-Host "7. Reset to .env.example"
  Write-Host ''
  $choice = Read-Host 'Choose item to change, or press Enter to return'

  switch ($choice) {
    '1' {
      $value = Read-Host 'New Web port'
      $port = Test-PortValue $value
      Set-EnvValue -Name 'ZABBIX_WEB_PORT' -Value $port
      Write-Host 'Web port updated. Restart Zabbix to apply.'
    }
    '2' {
      $value = Read-Host 'New Zabbix Server port'
      $port = Test-PortValue $value
      Set-EnvValue -Name 'ZABBIX_SERVER_PORT' -Value $port
      Write-Host 'Server port updated. Restart Zabbix to apply.'
    }
    '3' {
      $value = Read-Host 'New timezone, for example Asia/Shanghai'
      if (-not $value) { throw 'Timezone cannot be empty.' }
      Set-EnvValue -Name 'PHP_TZ' -Value $value
      Write-Host 'Timezone updated. Restart Zabbix to apply.'
    }
    '4' {
      $value = Read-Host 'New image tag, for example alpine-7.0-latest'
      if (-not $value) { throw 'Image tag cannot be empty.' }
      Set-EnvValue -Name 'ZABBIX_IMAGE_TAG' -Value $value
      Write-Host 'Image tag updated. Run Update to pull and recreate containers.'
    }
    '5' {
      $value = Read-Host 'New MySQL root password'
      if (-not $value) { throw 'Password cannot be empty.' }
      Set-EnvValue -Name 'MYSQL_ROOT_PASSWORD' -Value $value
      Write-Host 'Password updated in .env. Existing initialized databases must be changed manually inside MySQL.'
    }
    '6' {
      $value = Read-Host 'New Zabbix DB password'
      if (-not $value) { throw 'Password cannot be empty.' }
      Set-EnvValue -Name 'MYSQL_PASSWORD' -Value $value
      Write-Host 'Password updated in .env. Existing initialized databases must be changed manually inside MySQL.'
    }
    '7' {
      if (Test-Path -LiteralPath '.env') {
        Copy-Item -LiteralPath '.env' -Destination ".env.backup.$(Get-Date -Format yyyyMMddHHmmss)" -Force
      }
      Copy-Item -LiteralPath '.env.example' -Destination '.env' -Force
      Write-Host '.env reset from .env.example. Previous file was backed up.'
    }
    default {
      Write-Host 'No changes.'
    }
  }

  Test-ComposeConfig
}

function Invoke-Repair {
  Write-Title 'Repair'
  $mode = Ensure-Docker
  if ($mode -eq 'wsl') {
    Invoke-WslZabbix -LinuxAction start
    return
  }

  Ensure-EnvFile
  Test-ComposeConfig

  $webPort = Test-PortValue (Get-EnvValue -Name 'ZABBIX_WEB_PORT' -DefaultValue '8080')
  $serverPort = Test-PortValue (Get-EnvValue -Name 'ZABBIX_SERVER_PORT' -DefaultValue '10051')
  Write-Host "Configured Web port: $webPort"
  Write-Host "Configured Server port: $serverPort"

  Write-Host 'Recreating containers without deleting data...'
  docker compose up -d --force-recreate
  if ($LASTEXITCODE -ne 0) {
    throw 'Container repair failed.'
  }

  $ready = Wait-ZabbixReady -Seconds 180
  if ($ready) {
    Write-Host 'Repair completed. Zabbix Web is reachable.'
  } else {
    Write-Host 'Repair completed, but Web readiness timed out. Run HealthCheck for details.' -ForegroundColor Yellow
  }
}

function Invoke-Backup {
  Write-Title 'Database backup'
  $mode = Ensure-Docker
  if ($mode -eq 'wsl') {
    throw 'Backup from Windows Server WSL mode is not implemented in this Windows wrapper. Use docker exec inside Ubuntu-24.04.'
  }

  Ensure-EnvFile
  $rootPassword = Get-EnvValue -Name 'MYSQL_ROOT_PASSWORD' -DefaultValue ''
  if (-not $rootPassword) {
    throw 'MYSQL_ROOT_PASSWORD is missing.'
  }

  if (-not (Test-Path -LiteralPath '.\backups')) {
    New-Item -ItemType Directory -Path '.\backups' | Out-Null
  }

  $file = Join-Path (Resolve-Path '.\backups') "zabbix-db-$(Get-Date -Format yyyyMMdd-HHmmss).sql"
  docker exec -e "MYSQL_PWD=$rootPassword" zabbix-mysql mysqldump -uroot zabbix | Set-Content -LiteralPath $file -Encoding UTF8
  if ($LASTEXITCODE -ne 0) {
    throw 'Database backup failed.'
  }
  Write-Host "Backup created: $file"
}

function Invoke-ResetData {
  Write-Title 'Reset data'
  Write-Host 'This deletes all Zabbix database data for this local stack.'
  $answer = Read-Host 'Type DELETE to continue'
  if ($answer -ne 'DELETE') {
    Write-Host 'Cancelled.'
    return
  }

  $mode = Ensure-Docker
  if ($mode -eq 'wsl') {
    throw 'Reset from Windows Server WSL mode is not implemented in this Windows wrapper.'
  }

  docker compose down -v
  if ($LASTEXITCODE -ne 0) {
    throw 'Failed to reset data.'
  }
  Write-Host 'Data reset completed. Run Start to initialize a fresh Zabbix database.'
}

function Get-ComposeImages {
  Ensure-EnvFile
  $images = docker compose --env-file .env config --images
  if ($LASTEXITCODE -ne 0) {
    throw 'Failed to read image list from compose.yaml.'
  }
  return $images | Where-Object { $_ } | Sort-Object -Unique
}

function Get-ImageId {
  param([string]$Image)

  $id = docker image inspect --format '{{.Id}}' $Image 2>$null
  if ($LASTEXITCODE -ne 0) {
    return ''
  }
  return ($id | Select-Object -First 1).Trim()
}

function Invoke-ImageRefresh {
  param([switch]$Apply)

  $null = Ensure-Docker
  Ensure-EnvFile
  $images = Get-ComposeImages

  Write-Host 'Images in this stack:'
  $images | ForEach-Object { Write-Host "  - $_" }
  Write-Host ''

  $changed = $false
  foreach ($image in $images) {
    $before = Get-ImageId -Image $image

    if ($Apply) {
      Write-Host "Pulling $image ..."
      docker pull $image
    } else {
      Write-Host "Checking $image ..."
      docker pull $image
    }

    if ($LASTEXITCODE -ne 0) {
      throw "Failed to download image: $image"
    }

    $after = Get-ImageId -Image $image
    if (-not $before) {
      Write-Host "  Downloaded: $image"
      $changed = $true
    } elseif ($before -ne $after) {
      Write-Host "  Updated: $image"
      $changed = $true
    } else {
      Write-Host "  Current: $image"
    }
  }

  if ($Apply) {
    Write-Host ''
    if ($changed) {
      Write-Host 'Image updates were downloaded. Recreating containers...'
    } else {
      Write-Host 'No new image IDs were found. Recreating containers with the current images...'
    }
    docker compose up -d
    if ($LASTEXITCODE -ne 0) {
      throw 'Failed to recreate containers after update.'
    }
  } elseif (-not $changed) {
    Write-Host ''
    Write-Host 'No image updates were found.'
  }
}

try {
  switch ($Action) {
    'Start' {
      Write-Title 'One-click startup for Windows'
      $mode = Ensure-Docker
      if ($mode -eq 'wsl') {
        Invoke-WslZabbix -LinuxAction start
        return
      }
      Ensure-EnvFile
      Test-ComposeConfig
      Test-PortsBeforeStart
      Write-Host 'Pulling required images. This may take several minutes the first time.'
      docker compose pull
      if ($LASTEXITCODE -ne 0) { throw 'Failed to pull Docker images.' }
      Write-Host 'Starting Zabbix...'
      docker compose up -d
      if ($LASTEXITCODE -ne 0) { throw 'Failed to start Zabbix.' }
      $webPort = Get-EnvValue -Name 'ZABBIX_WEB_PORT' -DefaultValue '8080'
      Write-Host ''
      Write-Host 'Zabbix is starting in the background.'
      Write-Host "Open: http://localhost:$webPort"
      Write-Host 'Login: Admin / zabbix'
      Write-Host ''
      Write-Host 'First startup can take 1-3 minutes while the database initializes.'
      if ($OpenBrowser) {
        Start-Process "http://localhost:$webPort"
      }
    }
    'Stop' {
      Write-Title 'Stopping Windows stack'
      $mode = Ensure-Docker
      if ($mode -eq 'wsl') {
        Invoke-WslZabbix -LinuxAction stop
        return
      }
      docker compose down
      if ($LASTEXITCODE -ne 0) { throw 'Failed to stop Zabbix.' }
    }
    'Restart' {
      Write-Title 'Restarting Windows stack'
      $mode = Ensure-Docker
      if ($mode -eq 'wsl') {
        Invoke-WslZabbix -LinuxAction stop
        Invoke-WslZabbix -LinuxAction start
        return
      }
      Ensure-EnvFile
      Test-ComposeConfig
      Test-PortsBeforeStart
      docker compose down
      if ($LASTEXITCODE -ne 0) { throw 'Failed to stop Zabbix.' }
      docker compose up -d
      if ($LASTEXITCODE -ne 0) { throw 'Failed to restart Zabbix.' }
    }
    'Status' {
      Write-Title 'Container status'
      $mode = Ensure-Docker
      if ($mode -eq 'wsl') {
        Invoke-WslZabbix -LinuxAction status
        return
      }
      docker compose ps
      Write-Host ''
      docker compose logs --tail=100 zabbix-server zabbix-web zabbix-web-service
    }
    'Logs' {
      Write-Title 'Logs'
      $mode = Ensure-Docker
      if ($mode -eq 'wsl') {
        Invoke-WslZabbix -LinuxAction status
        return
      }
      docker compose logs --tail=200 mysql zabbix-server zabbix-web zabbix-agent2 zabbix-java-gateway zabbix-web-service
    }
    'Open' {
      Ensure-EnvFile
      $webPort = Get-EnvValue -Name 'ZABBIX_WEB_PORT' -DefaultValue '8080'
      Start-Process "http://localhost:$webPort"
    }
    'CheckUpdate' {
      Write-Title 'Checking image updates'
      $mode = Ensure-Docker
      if ($mode -eq 'wsl') {
        Invoke-WslZabbix -LinuxAction check-update
        return
      }
      Invoke-ImageRefresh
    }
    'Update' {
      Write-Title 'Downloading updates and restarting'
      $mode = Ensure-Docker
      if ($mode -eq 'wsl') {
        Invoke-WslZabbix -LinuxAction update
        return
      }
      Invoke-ImageRefresh -Apply
    }
    'Configure' {
      Invoke-Configure
    }
    'HealthCheck' {
      Invoke-HealthCheck
    }
    'Repair' {
      Invoke-Repair
    }
    'Backup' {
      Invoke-Backup
    }
    'ResetData' {
      Invoke-ResetData
    }
  }
} catch {
  Write-Host ''
  Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}
