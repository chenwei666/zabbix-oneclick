import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


APP_NAME = "ZabbixOneClick"
APP_VERSION = "1.0.2"
PAYLOAD_DIR_NAME = "zabbix_payload"

PAYLOAD_FILES = [
    "compose.yaml",
    ".env.example",
    "README.md",
    "README.en.md",
    "LICENSE",
    "zabbix-windows.ps1",
    "install-docker-windows.ps1",
    "install-docker-windows.bat",
    "start-zabbix-windows.bat",
    "stop-zabbix-windows.bat",
    "restart-zabbix-windows.bat",
    "status-zabbix-windows.bat",
    "health-check-zabbix-windows.bat",
    "configure-zabbix-windows.bat",
    "check-update-zabbix-windows.bat",
    "update-zabbix-windows.bat",
    "repair-zabbix-windows.bat",
    "logs-zabbix-windows.bat",
    "open-zabbix-windows.bat",
    "backup-zabbix-windows.bat",
    "reset-zabbix-data-windows.bat",
    "install-docker-linux.sh",
    "start-zabbix-linux.sh",
    "stop-zabbix-linux.sh",
    "status-zabbix-linux.sh",
    "check-update-zabbix-linux.sh",
    "update-zabbix-linux.sh",
    "zabbix-start.desktop",
    "zabbix-stop.desktop",
    "zabbix-update.desktop",
]

WINDOWS_ACTIONS = {
    "1": ("Start", "启动 Zabbix / Start Zabbix"),
    "2": ("Open", "打开网页 / Open Web UI"),
    "3": ("Status", "查看状态 / Status"),
    "4": ("HealthCheck", "健康检查 / Health Check"),
    "5": ("Configure", "修改配置 / Configure"),
    "6": ("CheckUpdate", "检查更新 / Check Updates"),
    "7": ("Update", "下载更新并重启 / Update and Restart"),
    "8": ("Repair", "问题修复 / Repair"),
    "9": ("Backup", "备份数据库 / Backup Database"),
    "10": ("Logs", "查看日志 / View Logs"),
    "11": ("Restart", "重启 Zabbix / Restart Zabbix"),
    "12": ("Stop", "停止 Zabbix / Stop Zabbix"),
    "13": ("ResetData", "清空重装 / Reset Data"),
    "14": ("InstallDocker", "安装 Docker / Install Docker"),
    "15": ("ShowFolder", "打开部署目录 / Open Deployment Folder"),
}

ALIASES = {
    "start": "Start",
    "open": "Open",
    "status": "Status",
    "health": "HealthCheck",
    "health-check": "HealthCheck",
    "configure": "Configure",
    "config": "Configure",
    "check": "CheckUpdate",
    "check-update": "CheckUpdate",
    "update": "Update",
    "repair": "Repair",
    "backup": "Backup",
    "logs": "Logs",
    "restart": "Restart",
    "stop": "Stop",
    "reset": "ResetData",
    "reset-data": "ResetData",
    "install-docker": "InstallDocker",
    "folder": "ShowFolder",
}


def app_root() -> Path:
    base = os.environ.get("ZABBIX_ONECLICK_HOME")
    if base:
        return Path(base).expanduser().resolve()
    if platform.system().lower() == "windows":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")) / PAYLOAD_DIR_NAME
    return Path(__file__).resolve().parent


def extract_payload(target: Path) -> None:
    source_root = resource_root()
    target.mkdir(parents=True, exist_ok=True)

    for name in PAYLOAD_FILES:
        source = source_root / name
        if not source.exists():
            raise FileNotFoundError(f"Missing bundled file: {name}")

        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    env_file = target / ".env"
    if not env_file.exists():
        shutil.copy2(target / ".env.example", env_file)


def run_windows(action: str, root: Path) -> int:
    if action == "ShowFolder":
        subprocess.Popen(["explorer", str(root)])
        return 0

    if action == "InstallDocker":
        script = root / "install-docker-windows.ps1"
        args = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
        ]
    else:
        script = root / "zabbix-windows.ps1"
        args = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-Action",
            action,
        ]
        if action == "Start":
            args.append("-OpenBrowser")

    return subprocess.call(args, cwd=root)


def run_linux(action: str, root: Path) -> int:
    commands = {
        "Start": ["bash", str(root / "start-zabbix-linux.sh"), "start"],
        "Restart": ["bash", "-lc", f"cd '{root}' && ./stop-zabbix-linux.sh && ./start-zabbix-linux.sh"],
        "CheckUpdate": ["bash", str(root / "check-update-zabbix-linux.sh")],
        "Update": ["bash", str(root / "update-zabbix-linux.sh")],
        "Status": ["bash", str(root / "status-zabbix-linux.sh")],
        "Logs": ["bash", str(root / "status-zabbix-linux.sh")],
        "HealthCheck": ["bash", str(root / "status-zabbix-linux.sh")],
        "Repair": ["bash", str(root / "start-zabbix-linux.sh"), "start"],
        "Stop": ["bash", str(root / "stop-zabbix-linux.sh")],
        "InstallDocker": ["bash", str(root / "install-docker-linux.sh")],
        "ShowFolder": ["bash", "-lc", f"cd '{root}' && pwd"],
    }
    command = commands.get(action)
    if not command:
        print(f"Action is not available on Linux yet: {action}")
        return 1
    return subprocess.call(command, cwd=root)


def usage() -> str:
    return (
        "Usage: ZabbixOneClickFull.exe "
        "[start|open|status|health-check|configure|check-update|update|repair|backup|logs|restart|stop|reset-data|install-docker|folder]"
    )


def select_action() -> str:
    print()
    print(f"Zabbix One-Click Full {APP_VERSION} / Zabbix 一键部署完整版 {APP_VERSION}")
    print()
    for key, (_, label) in WINDOWS_ACTIONS.items():
        print(f"{key}. {label}")
    print()
    choice = input("请选择操作 / Select an option [1]: ").strip() or "1"
    return WINDOWS_ACTIONS.get(choice, WINDOWS_ACTIONS["1"])[0]


def main() -> int:
    root = app_root()
    extract_payload(root)
    os.chdir(root)

    print(f"部署目录: {root}")

    if len(sys.argv) > 1:
        requested = sys.argv[1].strip().lower()
        action = ALIASES.get(requested)
        if not action:
            print(usage())
            return 1
    else:
        action = select_action()

    if platform.system().lower() == "windows":
        code = run_windows(action, root)
    else:
        code = run_linux(action, root)

    if len(sys.argv) == 1:
        input("按 Enter 退出 / Press Enter to exit...")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
