import os
import platform
import subprocess
import sys
from pathlib import Path


if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).resolve().parent
else:
    ROOT = Path(__file__).resolve().parent


def run_windows(action: str) -> int:
    script = ROOT / "zabbix-windows.ps1"
    if not script.exists():
        print(f"Missing {script}")
        return 1

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
    return subprocess.call(args, cwd=ROOT)


def run_linux(action: str) -> int:
    commands = {
        "Start": ["bash", str(ROOT / "start-zabbix-linux.sh"), "start"],
        "Restart": ["bash", "-lc", f"cd '{ROOT}' && ./stop-zabbix-linux.sh && ./start-zabbix-linux.sh"],
        "CheckUpdate": ["bash", str(ROOT / "check-update-zabbix-linux.sh")],
        "Update": ["bash", str(ROOT / "update-zabbix-linux.sh")],
        "Status": ["bash", str(ROOT / "status-zabbix-linux.sh")],
        "Logs": ["bash", str(ROOT / "status-zabbix-linux.sh")],
        "HealthCheck": ["bash", str(ROOT / "status-zabbix-linux.sh")],
        "Repair": ["bash", str(ROOT / "start-zabbix-linux.sh"), "start"],
        "Stop": ["bash", str(ROOT / "stop-zabbix-linux.sh")],
    }
    command = commands.get(action)
    if not command:
        print(f"Action is not available on Linux yet: {action}")
        return 1

    script_path = Path(command[-1]) if command[-1].endswith(".sh") else None
    if script_path and not script_path.exists():
        print(f"Missing {script_path}")
        return 1
    return subprocess.call(command, cwd=ROOT)


def run(action: str) -> int:
    if action == "InstallDocker":
        if platform.system().lower() == "windows":
            return subprocess.call(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ROOT / "install-docker-windows.ps1"),
                ],
                cwd=ROOT,
            )
        return subprocess.call(["bash", str(ROOT / "install-docker-linux.sh")], cwd=ROOT)

    if platform.system().lower() == "windows":
        return run_windows(action)
    return run_linux(action)


def main() -> int:
    actions = {
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
    }

    if len(sys.argv) > 1:
        requested = sys.argv[1].strip().lower()
        aliases = {
            "start": "Start",
            "open": "Open",
            "check": "CheckUpdate",
            "check-update": "CheckUpdate",
            "update": "Update",
            "status": "Status",
            "health": "HealthCheck",
            "health-check": "HealthCheck",
            "configure": "Configure",
            "config": "Configure",
            "repair": "Repair",
            "backup": "Backup",
            "logs": "Logs",
            "restart": "Restart",
            "stop": "Stop",
            "reset": "ResetData",
            "reset-data": "ResetData",
            "install-docker": "InstallDocker",
        }
        action = aliases.get(requested)
        if not action:
            print(
                "Usage: ZabbixOneClick.exe "
                "[start|open|status|health-check|configure|check-update|update|repair|backup|logs|restart|stop|reset-data|install-docker]"
            )
            return 1
        return run(action)

    print()
    print("Zabbix One-Click Launcher / Zabbix 一键部署启动器")
    print()
    for key, (_, label) in actions.items():
        print(f"{key}. {label}")
    print()

    choice = input("请选择操作 / Select an option [1]: ").strip() or "1"
    action = actions.get(choice, actions["1"])[0]
    code = run(action)
    input("按 Enter 退出 / Press Enter to exit...")
    return code


if __name__ == "__main__":
    os.chdir(ROOT)
    raise SystemExit(main())
