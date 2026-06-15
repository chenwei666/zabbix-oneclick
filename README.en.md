# Zabbix One-Click

Zabbix One-Click is an open-source, beginner-friendly deployment package for running Zabbix on Windows, Windows Server, and Linux.

The recommended download for beginners is:

```text
ZabbixOneClickFull.exe
```

It is a single-file launcher. On first run, it extracts the deployment files to:

```text
%LOCALAPPDATA%\ZabbixOneClick
```

## Features

- One-click Zabbix startup
- Automatic Docker installation guidance or bootstrap
- Windows 10/11 Docker Desktop support
- Windows Server WSL2 + Ubuntu + Docker Engine path
- Linux Docker Engine installer script
- Docker Compose stack for MySQL, Zabbix Server, Web UI, Agent2, Java Gateway, and Web Service
- Port conflict checks
- Configuration menu for ports, timezone, image tag, and database password
- Update check and update/recreate workflow
- Health check
- Repair without deleting data
- Database backup
- Reset/reinstall with explicit confirmation
- Bilingual Chinese/English launcher menu

## Quick Start

On Windows, run:

```text
ZabbixOneClickFull.exe
```

Choose:

```text
1. Start Zabbix
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

Change the default password after first login.

## Linux

Linux users can run:

```bash
chmod +x *.sh
./start-zabbix-linux.sh
```

If Docker is missing, the script can install Docker Engine using Docker's official convenience script.

## Update

Use the launcher menu:

```text
Check Updates
Update and Restart
```

The updater pulls the Docker images defined by `compose.yaml` and recreates containers with the current images.

## License

MIT License.
