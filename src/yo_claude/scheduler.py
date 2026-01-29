"""OS scheduler installation for yo-claude."""

import subprocess
import sys
from pathlib import Path
from typing import Tuple

from .config import Config, load_config


# --- macOS LaunchAgent ---

LAUNCHAGENT_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.yo-claude</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>yo_claude</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{user_path}</string>
    </dict>
    <key>WorkingDirectory</key>
    <string>/tmp</string>
    <key>StartInterval</key>
    <integer>{interval_seconds}</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_path}</string>
    <key>StandardErrorPath</key>
    <string>{log_path}</string>
</dict>
</plist>
"""


def get_launchagent_path() -> Path:
    """Get the path to the LaunchAgent plist."""
    return Path.home() / "Library" / "LaunchAgents" / "com.yo-claude.plist"


def install_macos(config: Config) -> Tuple[bool, str]:
    """Install LaunchAgent on macOS."""
    import os

    plist_path = get_launchagent_path()
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    # Get paths - capture user's PATH so claude (node) works
    python_path = sys.executable
    log_path = Path.home() / ".yo-claude" / "yo-claude.log"
    interval_seconds = config.check_interval * 60
    user_path = os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin")

    # Write plist
    plist_content = LAUNCHAGENT_PLIST.format(
        python_path=python_path, interval_seconds=interval_seconds, log_path=log_path, user_path=user_path
    )
    plist_path.write_text(plist_content, encoding="utf-8")

    # Unload if already loaded (ignore errors)
    subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)

    # Load the agent
    result = subprocess.run(["launchctl", "load", str(plist_path)], capture_output=True, text=True)

    if result.returncode != 0:
        return False, f"Failed to load LaunchAgent: {result.stderr}"

    return True, f"Installed LaunchAgent at {plist_path}"


def uninstall_macos() -> Tuple[bool, str]:
    """Uninstall LaunchAgent on macOS."""
    plist_path = get_launchagent_path()

    if not plist_path.exists():
        return True, "LaunchAgent not installed"

    # Unload
    subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)

    # Remove file
    plist_path.unlink()

    return True, f"Removed LaunchAgent from {plist_path}"


# --- Linux systemd ---

SYSTEMD_SERVICE = """[Unit]
Description=yo-claude session timer helper

[Service]
Type=oneshot
ExecStart={python_path} -m yo_claude
"""

SYSTEMD_TIMER = """[Unit]
Description=Run yo-claude periodically

[Timer]
OnBootSec=1min
OnUnitActiveSec={interval_minutes}min
Persistent=true

[Install]
WantedBy=timers.target
"""


def get_systemd_dir() -> Path:
    """Get the systemd user directory."""
    return Path.home() / ".config" / "systemd" / "user"


def install_linux(config: Config) -> Tuple[bool, str]:
    """Install systemd user timer on Linux."""
    systemd_dir = get_systemd_dir()
    systemd_dir.mkdir(parents=True, exist_ok=True)

    service_path = systemd_dir / "yo-claude.service"
    timer_path = systemd_dir / "yo-claude.timer"

    python_path = sys.executable

    # Write service file
    service_content = SYSTEMD_SERVICE.format(python_path=python_path)
    service_path.write_text(service_content, encoding="utf-8")

    # Write timer file
    timer_content = SYSTEMD_TIMER.format(interval_minutes=config.check_interval)
    timer_path.write_text(timer_content, encoding="utf-8")

    # Reload systemd
    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)

    # Enable and start timer
    result = subprocess.run(
        ["systemctl", "--user", "enable", "--now", "yo-claude.timer"], capture_output=True, text=True
    )

    if result.returncode != 0:
        return False, f"Failed to enable timer: {result.stderr}"

    return True, f"Installed systemd timer at {timer_path}"


def uninstall_linux() -> Tuple[bool, str]:
    """Uninstall systemd user timer on Linux."""
    systemd_dir = get_systemd_dir()
    service_path = systemd_dir / "yo-claude.service"
    timer_path = systemd_dir / "yo-claude.timer"

    # Stop and disable timer
    subprocess.run(["systemctl", "--user", "disable", "--now", "yo-claude.timer"], capture_output=True)

    # Remove files
    removed = []
    for path in [service_path, timer_path]:
        if path.exists():
            path.unlink()
            removed.append(str(path))

    # Reload systemd
    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)

    if removed:
        return True, f"Removed: {', '.join(removed)}"
    return True, "systemd timer not installed"


# --- Windows Task Scheduler ---


def get_task_name() -> str:
    """Get the Windows task name."""
    return "yo-claude"


def install_windows(config: Config) -> Tuple[bool, str]:
    """Install Windows scheduled task."""
    python_path = sys.executable
    task_name = get_task_name()

    # Delete existing task if present (ignore errors)
    subprocess.run(["schtasks", "/delete", "/tn", task_name, "/f"], capture_output=True)

    # Create new task
    # Run every N minutes
    result = subprocess.run(
        [
            "schtasks",
            "/create",
            "/tn",
            task_name,
            "/tr",
            f'"{python_path}" -m yo_claude',
            "/sc",
            "minute",
            "/mo",
            str(config.check_interval),
            "/f",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return False, f"Failed to create scheduled task: {result.stderr}"

    return True, f"Created scheduled task '{task_name}'"


def uninstall_windows() -> Tuple[bool, str]:
    """Uninstall Windows scheduled task."""
    task_name = get_task_name()

    result = subprocess.run(["schtasks", "/delete", "/tn", task_name, "/f"], capture_output=True, text=True)

    if result.returncode != 0:
        if "cannot find" in result.stderr.lower() or "not found" in result.stderr.lower():
            return True, "Scheduled task not installed"
        return False, f"Failed to delete scheduled task: {result.stderr}"

    return True, f"Removed scheduled task '{task_name}'"


# --- Cross-platform interface ---


def install(config: Config = None) -> Tuple[bool, str]:
    """Install the scheduler for the current OS."""
    if config is None:
        config = load_config()

    if sys.platform == "darwin":
        return install_macos(config)
    elif sys.platform == "linux":
        return install_linux(config)
    elif sys.platform == "win32":
        return install_windows(config)
    else:
        return False, f"Unsupported platform: {sys.platform}"


def uninstall() -> Tuple[bool, str]:
    """Uninstall the scheduler for the current OS."""
    if sys.platform == "darwin":
        return uninstall_macos()
    elif sys.platform == "linux":
        return uninstall_linux()
    elif sys.platform == "win32":
        return uninstall_windows()
    else:
        return False, f"Unsupported platform: {sys.platform}"


def get_scheduler_status() -> dict:
    """Check if the scheduler is installed."""
    status = {"platform": sys.platform, "installed": False, "details": None}

    if sys.platform == "darwin":
        plist_path = get_launchagent_path()
        if plist_path.exists():
            status["installed"] = True
            status["details"] = str(plist_path)

    elif sys.platform == "linux":
        timer_path = get_systemd_dir() / "yo-claude.timer"
        if timer_path.exists():
            status["installed"] = True
            status["details"] = str(timer_path)

    elif sys.platform == "win32":
        result = subprocess.run(["schtasks", "/query", "/tn", get_task_name()], capture_output=True)
        if result.returncode == 0:
            status["installed"] = True
            status["details"] = f"Task: {get_task_name()}"

    return status
