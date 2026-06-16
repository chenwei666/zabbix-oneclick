import locale
import os
import platform
import queue
import shutil
import subprocess
import sys
import threading
from pathlib import Path


APP_NAME = "ZabbixOneClick"
APP_VERSION = "1.0.3"
EXE_NAME = f"ZabbixOneClick-v{APP_VERSION}.exe"
ZIP_NAME = f"ZabbixOneClick-v{APP_VERSION}.zip"
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
    "1": ("Start", "启动部署", "Start Zabbix"),
    "2": ("Open", "打开网页", "Open Web UI"),
    "3": ("Status", "查看状态", "Status"),
    "4": ("HealthCheck", "健康检查", "Health Check"),
    "5": ("Configure", "修改配置", "Configure"),
    "6": ("CheckUpdate", "检查更新", "Check Updates"),
    "7": ("Update", "更新并重启", "Update and Restart"),
    "8": ("Repair", "问题修复", "Repair"),
    "9": ("Backup", "备份数据库", "Backup Database"),
    "10": ("Logs", "查看日志", "View Logs"),
    "11": ("Restart", "重启服务", "Restart Zabbix"),
    "12": ("Stop", "停止服务", "Stop Zabbix"),
    "13": ("ResetData", "清空重装", "Reset Data"),
    "14": ("InstallDocker", "安装 Docker", "Install Docker"),
    "15": ("ShowFolder", "打开目录", "Open Folder"),
}

BUTTON_ACTIONS = [
    ("Start", "启动部署", "Start"),
    ("Open", "打开网页", "Open"),
    ("Status", "状态", "Status"),
    ("HealthCheck", "健康检查", "Health"),
    ("Configure", "修改配置", "Config"),
    ("CheckUpdate", "检查更新", "Check"),
    ("Update", "更新并重启", "Update"),
    ("Repair", "问题修复", "Repair"),
    ("Logs", "查看日志", "Logs"),
    ("Backup", "备份数据库", "Backup"),
    ("Restart", "重启", "Restart"),
    ("Stop", "停止", "Stop"),
    ("ResetData", "清空重装", "Reset"),
    ("InstallDocker", "安装 Docker", "Docker"),
    ("ShowFolder", "打开目录", "Folder"),
]

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

ENV_FIELDS = [
    ("ZABBIX_WEB_PORT", "Web 端口 / Web port"),
    ("ZABBIX_SERVER_PORT", "Server 端口 / Server port"),
    ("PHP_TZ", "时区 / Timezone"),
    ("ZABBIX_IMAGE_TAG", "Zabbix 镜像版本 / Image tag"),
    ("MYSQL_ROOT_PASSWORD", "MySQL root 密码 / MySQL root password"),
    ("MYSQL_PASSWORD", "Zabbix DB 密码 / Zabbix DB password"),
]


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


def powershell_command(action: str, root: Path) -> list[str]:
    if action == "InstallDocker":
        return [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(root / "install-docker-windows.ps1"),
        ]

    args = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(root / "zabbix-windows.ps1"),
        "-Action",
        action,
    ]
    if action == "Start":
        args.append("-OpenBrowser")
    if action == "ResetData":
        args.append("-Yes")
    return args


def run_windows(action: str, root: Path) -> int:
    if action == "ShowFolder":
        subprocess.Popen(["explorer", str(root)])
        return 0

    return subprocess.call(powershell_command(action, root), cwd=root)


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


def read_env(root: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    env_path = root / ".env"
    if not env_path.exists():
        shutil.copy2(root / ".env.example", env_path)

    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def write_env(root: Path, updates: dict[str, str]) -> None:
    env_path = root / ".env"
    if not env_path.exists():
        shutil.copy2(root / ".env.example", env_path)

    lines = env_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    seen = set()
    output = []
    for line in lines:
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key = line.split("=", 1)[0].strip()
            if key in updates:
                output.append(f"{key}={updates[key]}")
                seen.add(key)
                continue
        output.append(line)

    for key, value in updates.items():
        if key not in seen:
            output.append(f"{key}={value}")

    env_path.write_text("\n".join(output) + "\n", encoding="ascii", errors="ignore")


def usage() -> str:
    return (
        f"Usage: {EXE_NAME} "
        "[start|open|status|health-check|configure|check-update|update|repair|backup|logs|restart|stop|reset-data|install-docker|folder]"
    )


def launch_gui(root: Path) -> int:
    import tkinter as tk
    from tkinter import messagebox, scrolledtext, ttk

    command_queue: queue.Queue[tuple[str, str | int]] = queue.Queue()
    running = {"value": False}
    buttons: list[ttk.Button] = []

    app = tk.Tk()
    app.title(f"Zabbix One-Click v{APP_VERSION}")
    app.geometry("980x680")
    app.minsize(860, 560)

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Title.TLabel", font=("Microsoft YaHei UI", 15, "bold"))
    style.configure("Hint.TLabel", foreground="#555")
    style.configure("Action.TButton", padding=(10, 8))

    header = ttk.Frame(app, padding=(14, 12, 14, 8))
    header.pack(fill="x")
    ttk.Label(header, text=f"Zabbix 一键部署 / One-Click v{APP_VERSION}", style="Title.TLabel").pack(anchor="w")
    ttk.Label(header, text=f"部署目录 / Deployment folder: {root}", style="Hint.TLabel").pack(anchor="w", pady=(4, 0))

    body = ttk.Frame(app, padding=(14, 6, 14, 14))
    body.pack(fill="both", expand=True)

    sidebar = ttk.Frame(body)
    sidebar.pack(side="left", fill="y", padx=(0, 12))

    log_box = scrolledtext.ScrolledText(body, wrap="word", font=("Consolas", 10), height=28)
    log_box.pack(side="left", fill="both", expand=True)

    status_text = tk.StringVar(value="就绪 / Ready")
    status = ttk.Label(app, textvariable=status_text, anchor="w", padding=(14, 0, 14, 10))
    status.pack(fill="x")

    def append(text: str) -> None:
        log_box.insert("end", text)
        log_box.see("end")

    def set_busy(value: bool) -> None:
        running["value"] = value
        for button in buttons:
            button.configure(state=("disabled" if value else "normal"))

    def stream_action(action: str) -> None:
        if action == "ShowFolder":
            subprocess.Popen(["explorer", str(root)])
            return
        if action == "Open":
            run_windows("Open", root)
            return
        if action == "Configure":
            open_config_dialog()
            return
        if action == "ResetData" and not messagebox.askyesno(
            "清空重装 / Reset Data",
            "这会删除本地 Zabbix 数据库数据，确认继续吗？\nThis deletes the local Zabbix database data. Continue?",
        ):
            return
        if running["value"]:
            return

        set_busy(True)
        status_text.set(f"运行中 / Running: {action}")
        append(f"\n>>> {action}\n")

        def worker() -> None:
            startupinfo = None
            creationflags = 0
            if platform.system().lower() == "windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

            process = subprocess.Popen(
                powershell_command(action, root),
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding=locale.getpreferredencoding(False),
                errors="replace",
                bufsize=1,
                startupinfo=startupinfo,
                creationflags=creationflags,
            )
            assert process.stdout is not None
            for line in process.stdout:
                command_queue.put(("log", line))
            code = process.wait()
            command_queue.put(("done", code))

        threading.Thread(target=worker, daemon=True).start()

    def pump_queue() -> None:
        try:
            while True:
                kind, payload = command_queue.get_nowait()
                if kind == "log":
                    append(str(payload))
                elif kind == "done":
                    code = int(payload)
                    status_text.set("完成 / Completed" if code == 0 else f"失败 / Failed: exit {code}")
                    append(f"\n<<< Exit code: {code}\n")
                    set_busy(False)
        except queue.Empty:
            pass
        app.after(120, pump_queue)

    def open_config_dialog() -> None:
        values = read_env(root)
        dialog = tk.Toplevel(app)
        dialog.title("修改配置 / Configure")
        dialog.transient(app)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        entries: dict[str, ttk.Entry] = {}

        for row, (key, label) in enumerate(ENV_FIELDS):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=5, padx=(0, 12))
            entry = ttk.Entry(frame, width=36)
            entry.insert(0, values.get(key, ""))
            entry.grid(row=row, column=1, sticky="ew", pady=5)
            entries[key] = entry

        def save() -> None:
            updates = {key: entry.get().strip() for key, entry in entries.items()}
            try:
                for port_key in ("ZABBIX_WEB_PORT", "ZABBIX_SERVER_PORT"):
                    port = int(updates[port_key])
                    if port < 1 or port > 65535:
                        raise ValueError(port_key)
                write_env(root, updates)
            except Exception as exc:
                messagebox.showerror("保存失败 / Save failed", f"配置格式不正确: {exc}")
                return
            append("\n配置已保存。重启 Zabbix 后生效。\nConfiguration saved. Restart Zabbix to apply changes.\n")
            dialog.destroy()

        buttons_row = ttk.Frame(frame)
        buttons_row.grid(row=len(ENV_FIELDS), column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(buttons_row, text="取消 / Cancel", command=dialog.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons_row, text="保存 / Save", command=save).pack(side="right")

    for action, zh, en in BUTTON_ACTIONS:
        button = ttk.Button(sidebar, text=f"{zh}\n{en}", style="Action.TButton", command=lambda a=action: stream_action(a))
        button.pack(fill="x", pady=3)
        buttons.append(button)

    append(f"Zabbix One-Click v{APP_VERSION}\n")
    append("点击左侧按钮开始部署。日志会显示在这里。\nClick a button on the left to start. Logs appear here.\n")

    app.after(120, pump_queue)
    app.mainloop()
    return 0


def main() -> int:
    root = app_root()
    extract_payload(root)
    os.chdir(root)

    if len(sys.argv) > 1:
        requested = sys.argv[1].strip().lower()
        action = ALIASES.get(requested)
        if not action:
            print(usage())
            return 1
        if platform.system().lower() == "windows":
            return run_windows(action, root)
        return run_linux(action, root)

    if platform.system().lower() == "windows":
        return launch_gui(root)

    print(f"部署目录: {root}")
    return run_linux("Start", root)


if __name__ == "__main__":
    raise SystemExit(main())
