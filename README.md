# Zabbix 傻瓜式一键搭建方案 / Zabbix One-Click

开源协议：MIT License。English documentation: [README.en.md](README.en.md)

这是一套面向 Windows、Windows Server 和 Linux 的 Zabbix 本地一键部署方案。核心使用 Docker Compose，脚本会自动检测环境、下载镜像、启动服务、检查更新。

This is an open-source, beginner-friendly Zabbix deployment package for Windows, Windows Server, and Linux. It uses Docker Compose and includes automatic environment checks, image downloads, startup, update checks, repair tools, and backup helpers.

最简单用法：

- Windows 新手推荐：下载并双击 `ZabbixOneClick-v1.0.3.exe`
- 完整文件包：解压 `release\ZabbixOneClick-v1.0.3.zip`

新版 Windows EXE 是点击式界面，左侧按钮执行启动、状态、健康检查、更新、修复、备份、停止等操作，右侧显示实时日志。

默认启动组件：

- MySQL 8.0
- Zabbix Server
- Zabbix Web Nginx
- Zabbix Agent 2
- Zabbix Java Gateway，用于 JMX 监控
- Zabbix Web Service，用于报表、浏览器类能力等

默认使用 Zabbix 7.0 LTS Docker 镜像，适合长期稳定使用。

## 前置要求

必须先安装并启动 Docker，并且 Docker 必须处于 Linux containers 模式。

- Windows 10/11：安装 Docker Desktop，启动后等待 Docker 显示 running。
- Linux：安装 Docker Engine 和 Docker Compose v2 插件，并确保当前用户可以运行 `docker`。
- Windows Server：不要按普通 Windows 桌面方式处理。Docker 官方说明 Docker Desktop 不支持 Windows Server 2019/2022；建议使用 WSL2 + Ubuntu + Docker Engine，或其他能提供 Linux containers 的 Docker 环境。

脚本会检查：

- 是否存在 `docker`
- Docker 是否正在运行
- 是否支持 `docker compose`
- Docker 当前是否为 Linux containers 模式
- 是否已有可用的 WSL Docker 环境
- Windows Server 上会优先复用已有 WSL Docker

如果没有 Docker，启动器会尝试一键安装：

- Windows 10/11：如果 Docker Desktop 可用，直接使用 Docker Desktop；如果 Docker Desktop 不可用但 WSL 里已有 Docker Engine，会直接复用 WSL Docker 拉取镜像并部署；两者都没有时，优先通过 `winget install Docker.DockerDesktop` 安装 Docker Desktop。
- Windows Server：不安装 Docker Desktop。会先扫描所有 WSL 发行版，只要发现其中一个已有 Docker Engine + Compose，就直接使用它部署 Zabbix；如果没有，才启用 WSL2、安装 Ubuntu 24.04，并在 Ubuntu 内安装 Docker Engine。
- Linux：通过 Docker 官方 `get.docker.com` convenience script 安装 Docker Engine 和 Compose 插件。

涉及系统组件启用时，可能需要管理员权限或重启。重启后再次双击启动器即可继续。

## Windows 使用方式

双击启动：

```text
start-zabbix-windows.bat
```

启动成功后浏览器会自动打开：

```text
http://localhost:8080
```

默认登录：

```text
用户名：Admin
密码：zabbix
```

常用入口：

```text
start-zabbix-windows.bat        启动
stop-zabbix-windows.bat         停止
restart-zabbix-windows.bat      重启
status-zabbix-windows.bat       状态和日志
health-check-zabbix-windows.bat 健康检查
configure-zabbix-windows.bat    修改端口、时区、镜像版本等
check-update-zabbix-windows.bat 检查并拉取镜像更新，不重启容器
update-zabbix-windows.bat       拉取更新并重建容器
repair-zabbix-windows.bat       不删数据的修复重建
logs-zabbix-windows.bat         查看完整日志
backup-zabbix-windows.bat       备份数据库
reset-zabbix-data-windows.bat   清空数据库重装，需输入 DELETE 确认
install-docker-windows.bat      只安装 Docker，不启动 Zabbix
```

也可以直接运行 PowerShell 核心脚本：

```powershell
PowerShell -NoProfile -ExecutionPolicy Bypass -File .\zabbix-windows.ps1 -Action Start -OpenBrowser
PowerShell -NoProfile -ExecutionPolicy Bypass -File .\zabbix-windows.ps1 -Action Configure
PowerShell -NoProfile -ExecutionPolicy Bypass -File .\zabbix-windows.ps1 -Action HealthCheck
PowerShell -NoProfile -ExecutionPolicy Bypass -File .\zabbix-windows.ps1 -Action Repair
PowerShell -NoProfile -ExecutionPolicy Bypass -File .\zabbix-windows.ps1 -Action CheckUpdate
PowerShell -NoProfile -ExecutionPolicy Bypass -File .\zabbix-windows.ps1 -Action Update
```

## Linux 使用方式

图形桌面环境可双击：

```text
zabbix-start.desktop
zabbix-update.desktop
zabbix-stop.desktop
```

有些 Linux 桌面第一次会提示“信任并启动”或“Allow Launching”，确认即可。

终端方式：

```bash
chmod +x *.sh
./install-docker-linux.sh
./start-zabbix-linux.sh
./check-update-zabbix-linux.sh
./update-zabbix-linux.sh
./status-zabbix-linux.sh
./stop-zabbix-linux.sh
```

## EXE 封装

推荐使用单文件 GUI 版：

```text
ZabbixOneClick-v1.0.3.exe  单文件 GUI 版，内置 compose 和所有脚本，推荐发给新手
```

`ZabbixOneClick-v1.0.3.exe` 第一次运行时会自动解包到：

```text
%LOCALAPPDATA%\ZabbixOneClick
```

后续配置、`.env`、备份和日志都围绕这个部署目录工作。界面里有“打开目录”按钮。

源码入口：

```text
zabbix_launcher.py
zabbix_full_launcher.py
```

如果当前 Windows 已安装 Python，可执行：

```powershell
PowerShell -NoProfile -ExecutionPolicy Bypass -File .\build-zabbix-exe-windows.ps1
PowerShell -NoProfile -ExecutionPolicy Bypass -File .\build-full-exe-windows.ps1
```

构建成功后会生成：

```text
dist\ZabbixOneClick-v1.0.3.exe
release\ZabbixOneClick-v1.0.3.exe
```

这个 EXE 是一个点击式 GUI 启动器，支持：

- 启动 Zabbix
- 打开网页
- 查看状态
- 健康检查
- 修改配置
- 检查更新
- 下载更新并重启
- 问题修复
- 备份数据库
- 查看日志
- 重启 Zabbix
- 停止 Zabbix
- 清空重装
- 安装 Docker

注意：EXE 只封装启动控制逻辑，不会把 Docker、MySQL、Zabbix 镜像塞进 EXE。首次运行仍会通过 Docker 下载官方镜像。交付给别人时推荐直接发送 `release\ZabbixOneClick-v1.0.3.exe`。

## 打包交付

如果修改了源码后需要重新打包：

```powershell
PowerShell -NoProfile -ExecutionPolicy Bypass -File .\build-full-exe-windows.ps1
PowerShell -NoProfile -ExecutionPolicy Bypass -File .\package-zabbix-windows.ps1
```

打包脚本会生成：

```text
ZabbixOneClick-v1.0.3.exe
release\ZabbixOneClick-v1.0.3.exe
release\ZabbixOneClick-v1.0.3\
release\ZabbixOneClick-v1.0.3.zip
```

发给新手用户时，推荐直接给 `release\ZabbixOneClick-v1.0.3.exe`。

## 检查更新机制

更新检查基于当前 `compose.yaml` 和 `.env` 解析出的镜像列表，会覆盖所有本方案使用的镜像：

- `mysql:8.0`
- `zabbix/zabbix-server-mysql`
- `zabbix/zabbix-web-nginx-mysql`
- `zabbix/zabbix-agent2`
- `zabbix/zabbix-java-gateway`
- `zabbix/zabbix-web-service`

检查更新会执行镜像拉取并比较本地镜像 ID：

- 本地不存在：显示 `Downloaded`
- 镜像 ID 变化：显示 `Updated`
- 无变化：显示 `Current`

`check-update` 不重建容器；`update` 会拉取镜像并执行 `docker compose up -d`，确保容器使用当前镜像。这样即使你先执行过 `check-update`，再执行 `update` 也会重建到最新本地镜像。

## 常用配置

第一次启动时，如果不存在 `.env`，脚本会自动从 `.env.example` 创建一份。

可在 `.env` 里修改：

```text
ZABBIX_WEB_PORT=8080
ZABBIX_SERVER_PORT=10051
PHP_TZ=Asia/Bangkok
MYSQL_ROOT_PASSWORD=change_me_root_2026
MYSQL_PASSWORD=change_me_zabbix_2026
ZBX_CACHESIZE=256M
ZBX_TRENDCACHESIZE=128M
```

修改端口或密码后，重新双击启动脚本即可。数据库已经初始化后再改数据库密码，需要同步处理数据库内账号密码；新环境建议先改 `.env` 再首次启动。

小白建议不要直接编辑 `.env`，Windows 上直接运行：

```text
ZabbixOneClick-v1.0.3.exe -> 修改配置
```

启动前脚本会检查端口：

- Web 端口默认 `8080`
- Zabbix Server 端口默认 `10051`
- 如果端口被占用，会提示占用进程
- 端口冲突时，进入“修改配置”改成其他端口，例如 `18080`

## 问题修复

优先使用：

```text
ZabbixOneClick-v1.0.3.exe -> 健康检查
ZabbixOneClick-v1.0.3.exe -> 问题修复
```

健康检查会检查：

- Docker 是否可用
- Compose 配置是否正确
- 容器是否运行
- Web 是否可访问
- 数据库表和默认用户是否存在
- 最近的 Zabbix Server/Web 日志

问题修复会执行不删数据的容器重建：

```text
docker compose up -d --force-recreate
```

如果数据库已经损坏或半初始化，才使用“清空重装”。清空重装会删除当前 Zabbix 数据，必须输入 `DELETE` 确认。

## 备份

Windows 上可使用：

```text
ZabbixOneClick-v1.0.3.exe -> 备份数据库
```

备份文件会保存在：

```text
backups\
```

## 数据保存位置

数据库数据保存在 Docker 命名卷：

```text
zabbix-oneclick_mysql_data
```

普通停止不会删除数据。执行 `docker compose down` 后数据仍会保留。

如果需要彻底重装并清空数据，请在确认无用后手动执行：

```bash
docker compose down -v
```

## 首次启动说明

第一次启动需要下载镜像并初始化数据库，通常需要 1 到 3 分钟。浏览器如果一开始打不开，稍等后刷新即可。

上线或给他人访问前，请登录后立即修改默认 `Admin` 密码。

## 参考

- Zabbix 官方容器安装文档：`https://www.zabbix.com/documentation/current/en/manual/installation/containers`
- Docker Desktop Windows 安装要求：`https://docs.docker.com/desktop/setup/install/windows-install/`
