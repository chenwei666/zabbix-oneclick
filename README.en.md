# Zabbix One-Click

Zabbix One-Click is an open-source, beginner-friendly deployment package for running Zabbix on Windows, Windows Server, and Linux.

The recommended download for beginners is:

```text
ZabbixOneClick-v1.0.4.exe
```

It is a single-file GUI launcher. On first run, it extracts the deployment files to:

```text
%LOCALAPPDATA%\ZabbixOneClick
```

## Features

- One-click Zabbix startup
- Automatic Docker installation guidance or bootstrap
- Windows 10/11 Docker Desktop support
- Windows Server WSL2 + Ubuntu + Docker Engine path
- Automatic detection and reuse of existing Docker Engine inside any installed WSL distro
- Linux Docker Engine installer script
- Docker Compose stack for MySQL, Zabbix Server, Web UI, Agent2, Java Gateway, and Web Service
- Port conflict checks
- Configuration menu for ports, timezone, image tag, and database password
- Zabbix account password change through the Web API
- Update check and update/recreate workflow
- Health check
- Repair without deleting data
- Database backup
- Reset/reinstall with explicit confirmation
- Bilingual Chinese/English click-based GUI launcher

## Quick Start

On Windows, run:

```text
ZabbixOneClick-v1.0.4.exe
```

Click:

```text
Start
```

Then open:

```text
http://localhost:8080
```

Default login:

```text
User: Admin
Password: zabbix
```

You can change the default password from the launcher after first startup.

## Linux

Linux users can run:

```bash
chmod +x *.sh
./start-zabbix-linux.sh
```

If Docker is missing, the script can install Docker Engine using Docker's official convenience script.

## Windows and WSL Docker Detection

On Windows, the launcher checks environments in this order:

1. Native Docker Desktop with Linux containers.
2. Any installed WSL distro that already has Docker Engine and Docker Compose.
3. Docker installation/bootstrap flow.

On Windows Server, Docker Desktop is not used. The launcher first scans existing WSL distros and directly deploys through the first working Docker Engine it finds. If no WSL Docker environment exists, it installs/prepares Ubuntu 24.04 with Docker Engine.

## Update

Use the launcher menu:

```text
Check Updates
Update and Restart
```

The updater pulls the Docker images defined by `compose.yaml` and recreates containers with the current images.

## License

MIT License.
