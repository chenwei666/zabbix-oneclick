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
APP_VERSION = "1.0.4"
EXE_NAME = f"ZabbixOneClick-v{APP_VERSION}.exe"
ZIP_NAME = f"ZabbixOneClick-v{APP_VERSION}.zip"
PAYLOAD_DIR_NAME = "zabbix_payload"

PAYLOAD_FILES = [
    "compose.yaml",
    ".env.example",
    "README.md",
    "README.en.md",
    "LICENSE",
    "zabbix-oneclick.ico",
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
    "16": ("ChangeAdminPassword", "修改账号密码", "Change Account Password"),
}

BUTTON_ACTIONS = [
    ("Start", "启动部署", "Start", "RUN"),
    ("Open", "打开网页", "Open", "WEB"),
    ("HealthCheck", "健康检查", "Health", "OK"),
    ("Status", "查看状态", "Status", "PS"),
    ("Logs", "查看日志", "Logs", "LOG"),
    ("Configure", "修改配置", "Config", "CFG"),
    ("ChangeAdminPassword", "修改账号密码", "Password", "PWD"),
    ("CheckUpdate", "检查更新", "Check", "UP"),
    ("Update", "更新并重启", "Update", "UPD"),
    ("Repair", "问题修复", "Repair", "FIX"),
    ("Backup", "备份数据库", "Backup", "BAK"),
    ("Restart", "重启服务", "Restart", "RST"),
    ("Stop", "停止服务", "Stop", "OFF"),
    ("ResetData", "清空重装", "Reset", "DEL"),
    ("InstallDocker", "安装 Docker", "Docker", "DKR"),
    ("ShowFolder", "打开目录", "Folder", "DIR"),
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
    "password": "ChangeAdminPassword",
    "change-password": "ChangeAdminPassword",
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
        "[start|open|status|health-check|configure|check-update|update|repair|backup|logs|restart|stop|reset-data|password|install-docker|folder]"
    )


def launch_gui(root: Path) -> int:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk

    command_queue: queue.Queue[tuple[str, str | int]] = queue.Queue()
    running = {"value": False}
    password_user = {"value": "Admin"}
    buttons: list[tk.Button] = []

    app = tk.Tk()
    app.title(f"Zabbix One-Click v{APP_VERSION}")
    app.geometry("1180x760")
    app.minsize(960, 620)
    icon_path = resource_root() / "zabbix-oneclick.ico"
    if icon_path.exists() and platform.system().lower() == "windows":
        try:
            app.iconbitmap(str(icon_path))
        except tk.TclError:
            pass

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TFrame", background="#f3f5f8")
    style.configure("Title.TLabel", background="#f3f5f8", foreground="#111827", font=("Microsoft YaHei UI", 18, "bold"))
    style.configure("Hint.TLabel", background="#f3f5f8", foreground="#6b7280", font=("Microsoft YaHei UI", 9))
    style.configure("Card.TFrame", background="#ffffff", relief="flat")
    style.configure("CardTitle.TLabel", background="#ffffff", foreground="#6b7280", font=("Microsoft YaHei UI", 9))
    style.configure("CardValue.TLabel", background="#ffffff", foreground="#111827", font=("Microsoft YaHei UI", 13, "bold"))
    style.configure("Side.TFrame", background="#172033")
    style.configure("SideTitle.TLabel", background="#172033", foreground="#ffffff", font=("Microsoft YaHei UI", 12, "bold"))
    style.configure("SideHint.TLabel", background="#172033", foreground="#aeb7c8", font=("Microsoft YaHei UI", 9))
    style.configure("Danger.TButton", foreground="#b91c1c")

    app.configure(background="#f3f5f8")
    app.grid_rowconfigure(1, weight=1)
    app.grid_columnconfigure(0, weight=1)

    status_text = tk.StringVar(value="就绪 / Ready")
    web_url_text = tk.StringVar()
    port_text = tk.StringVar()
    deploy_text = tk.StringVar(value=str(root))
    login_text = tk.StringVar(value="Admin / zabbix")
    last_action_text = tk.StringVar(value="无 / None")

    def refresh_dashboard_values() -> None:
        values = read_env(root)
        web_port = values.get("ZABBIX_WEB_PORT", "8080")
        server_port = values.get("ZABBIX_SERVER_PORT", "10051")
        web_url_text.set(f"http://localhost:{web_port}")
        port_text.set(f"Web {web_port} / Server {server_port}")

    refresh_dashboard_values()

    header = ttk.Frame(app, padding=(18, 16, 18, 12))
    header.grid(row=0, column=0, sticky="ew")
    header.grid_columnconfigure(0, weight=1)
    ttk.Label(header, text=f"Zabbix 一键部署 / One-Click v{APP_VERSION}", style="Title.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Label(header, textvariable=deploy_text, style="Hint.TLabel").grid(row=1, column=0, sticky="ew", pady=(5, 0))

    status = ttk.Label(header, textvariable=status_text, anchor="e", style="Hint.TLabel")
    status.grid(row=0, column=1, rowspan=2, sticky="e")

    main = ttk.Frame(app, padding=(18, 0, 18, 16))
    main.grid(row=1, column=0, sticky="nsew")
    main.grid_rowconfigure(0, weight=1)
    main.grid_columnconfigure(1, weight=1)

    sidebar = ttk.Frame(main, style="Side.TFrame", padding=(12, 14))
    sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 14))
    sidebar.grid_columnconfigure(0, weight=1)
    ttk.Label(sidebar, text="操作面板", style="SideTitle.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Label(sidebar, text="Actions", style="SideHint.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 10))

    center = ttk.Frame(main)
    center.grid(row=0, column=1, sticky="nsew")
    center.grid_rowconfigure(2, weight=1)
    center.grid_columnconfigure(0, weight=1)

    cards = ttk.Frame(center)
    cards.grid(row=0, column=0, sticky="ew")
    for i in range(4):
        cards.grid_columnconfigure(i, weight=1, uniform="cards")

    def make_card(parent, col: int, title: str, variable: tk.StringVar) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=(14, 12))
        card.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0))
        ttk.Label(card, text=title, style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(card, textvariable=variable, style="CardValue.TLabel").pack(anchor="w", pady=(6, 0))

    make_card(cards, 0, "访问地址 / Web", web_url_text)
    make_card(cards, 1, "端口 / Ports", port_text)
    make_card(cards, 2, "默认账号 / Login", login_text)
    make_card(cards, 3, "最近操作 / Last Action", last_action_text)

    toolbar = ttk.Frame(center, padding=(0, 12, 0, 8))
    toolbar.grid(row=1, column=0, sticky="ew")
    toolbar.grid_columnconfigure(6, weight=1)
    ttk.Button(toolbar, text="打开网页", command=lambda: stream_action("Open")).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(toolbar, text="复制地址", command=lambda: copy_text(web_url_text.get())).grid(row=0, column=1, padx=(0, 8))
    ttk.Button(toolbar, text="修改密码", command=lambda: open_password_dialog()).grid(row=0, column=2, padx=(0, 8))
    ttk.Button(toolbar, text="清空日志", command=lambda: clear_log()).grid(row=0, column=3, padx=(0, 8))
    ttk.Button(toolbar, text="复制日志", command=lambda: copy_text(log_box.get("1.0", "end-1c"))).grid(row=0, column=4, padx=(0, 8))
    ttk.Button(toolbar, text="保存日志", command=lambda: save_log()).grid(row=0, column=5, padx=(0, 8))

    log_frame = ttk.Frame(center, style="Card.TFrame", padding=(1, 1))
    log_frame.grid(row=2, column=0, sticky="nsew")
    log_frame.grid_rowconfigure(0, weight=1)
    log_frame.grid_columnconfigure(0, weight=1)

    log_box = scrolledtext.ScrolledText(
        log_frame,
        wrap="word",
        font=("Cascadia Mono", 10),
        background="#0f172a",
        foreground="#dbeafe",
        insertbackground="#ffffff",
        relief="flat",
        borderwidth=0,
        padx=12,
        pady=10,
    )
    log_box.grid(row=0, column=0, sticky="nsew")

    def append(text: str) -> None:
        log_box.insert("end", text)
        log_box.see("end")

    def set_busy(value: bool) -> None:
        running["value"] = value
        for button in buttons:
            button.configure(state=("disabled" if value else "normal"))

    def copy_text(text: str) -> None:
        app.clipboard_clear()
        app.clipboard_append(text)
        status_text.set("已复制到剪贴板 / Copied")

    def clear_log() -> None:
        log_box.delete("1.0", "end")

    def save_log() -> None:
        log_dir = root / "logs"
        log_dir.mkdir(exist_ok=True)
        default = log_dir / "zabbix-oneclick-gui.log"
        path = filedialog.asksaveasfilename(
            title="保存日志 / Save log",
            initialdir=str(log_dir),
            initialfile=default.name,
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        Path(path).write_text(log_box.get("1.0", "end-1c"), encoding="utf-8")
        status_text.set(f"日志已保存 / Saved: {path}")

    def stream_action(action: str, env_overrides: dict[str, str] | None = None) -> None:
        if action == "ShowFolder":
            subprocess.Popen(["explorer", str(root)])
            return
        if action == "Open":
            run_windows("Open", root)
            return
        if action == "Configure":
            open_config_dialog()
            return
        if action == "ChangeAdminPassword":
            open_password_dialog()
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
        last_action_text.set(action)
        append(f"\n>>> {action}\n")

        def worker() -> None:
            startupinfo = None
            creationflags = 0
            if platform.system().lower() == "windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

            child_env = os.environ.copy()
            if env_overrides:
                child_env.update(env_overrides)

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
                env=child_env,
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
                    if code == 0 and last_action_text.get() == "ChangeAdminPassword":
                        login_text.set(f"{password_user['value']} / 已修改")
                    refresh_dashboard_values()
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
        dialog.resizable(True, False)

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(1, weight=1)
        entries: dict[str, ttk.Entry] = {}

        for row, (key, label) in enumerate(ENV_FIELDS):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=5, padx=(0, 12))
            entry = ttk.Entry(frame, width=42)
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
            refresh_dashboard_values()
            append("\n配置已保存。重启 Zabbix 后生效。\nConfiguration saved. Restart Zabbix to apply changes.\n")
            dialog.destroy()

        buttons_row = ttk.Frame(frame)
        buttons_row.grid(row=len(ENV_FIELDS), column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(buttons_row, text="取消 / Cancel", command=dialog.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons_row, text="保存 / Save", command=save).pack(side="right")

    def open_password_dialog() -> None:
        dialog = tk.Toplevel(app)
        dialog.title("修改 Zabbix 账号密码 / Change Password")
        dialog.transient(app)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)

        fields = [
            ("user", "用户名 / Username", "Admin", False),
            ("current", "当前密码 / Current password", "zabbix", True),
            ("new", "新密码 / New password", "", True),
            ("confirm", "确认新密码 / Confirm", "", True),
        ]
        entries: dict[str, ttk.Entry] = {}

        for row, (key, label, default, secret) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=5, padx=(0, 12))
            entry = ttk.Entry(frame, width=34, show="*" if secret else "")
            entry.insert(0, default)
            entry.grid(row=row, column=1, sticky="ew", pady=5)
            entries[key] = entry

        show_var = tk.BooleanVar(value=False)

        def toggle_secret() -> None:
            show = "" if show_var.get() else "*"
            for key in ("current", "new", "confirm"):
                entries[key].configure(show=show)

        ttk.Checkbutton(frame, text="显示密码 / Show passwords", variable=show_var, command=toggle_secret).grid(
            row=len(fields), column=1, sticky="w", pady=(6, 0)
        )

        def submit() -> None:
            user = entries["user"].get().strip() or "Admin"
            current = entries["current"].get()
            new = entries["new"].get()
            confirm = entries["confirm"].get()

            if not current:
                messagebox.showerror("缺少当前密码", "请输入当前 Zabbix 密码。")
                return
            if len(new) < 8:
                messagebox.showerror("密码太短", "新密码至少需要 8 个字符。")
                return
            if new != confirm:
                messagebox.showerror("两次密码不一致", "请重新确认新密码。")
                return

            env = {
                "ZABBIX_ADMIN_USER": user,
                "ZABBIX_CURRENT_ADMIN_PASSWORD": current,
                "ZABBIX_NEW_ADMIN_PASSWORD": new,
            }
            dialog.destroy()
            password_user["value"] = user
            stream_action("ChangeAdminPassword", env)

        buttons_row = ttk.Frame(frame)
        buttons_row.grid(row=len(fields) + 1, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(buttons_row, text="取消 / Cancel", command=dialog.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons_row, text="修改 / Change", command=submit).pack(side="right")

    def add_action_button(row: int, action: str, zh: str, en: str, badge: str) -> None:
        button = tk.Button(
            sidebar,
            text=f"{badge}  {zh}\n     {en}",
            anchor="w",
            justify="left",
            bg="#22304a",
            fg="#eef2ff",
            activebackground="#2f4264",
            activeforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=8,
            font=("Microsoft YaHei UI", 9),
            command=lambda a=action: stream_action(a),
        )
        button.grid(row=row, column=0, sticky="ew", pady=3)
        buttons.append(button)

    for idx, (action, zh, en, badge) in enumerate(BUTTON_ACTIONS, start=2):
        add_action_button(idx, action, zh, en, badge)

    append(f"Zabbix One-Click v{APP_VERSION}\n")
    append("点击左侧按钮开始部署、检查、修复和维护。日志会显示在这里。\n")
    append("Use the left panel to start, check, repair and maintain Zabbix. Logs appear here.\n")

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
