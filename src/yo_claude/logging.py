"""Simple logging for yo-claude."""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .config import get_log_path


MAX_LOG_LINES = 1000


def log(message: str, log_path: Optional[Path] = None) -> None:
    """Append a timestamped message to the log file."""
    if log_path is None:
        log_path = get_log_path()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}\n"

    # Append the new line
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)

    # Truncate if needed
    _truncate_if_needed(log_path)


def _truncate_if_needed(log_path: Path) -> None:
    """Keep only the last MAX_LOG_LINES lines."""
    try:
        lines = log_path.read_text(encoding="utf-8").splitlines()

        if len(lines) > MAX_LOG_LINES:
            # Keep the most recent lines
            lines = lines[-MAX_LOG_LINES:]
            log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        # Don't fail if truncation fails
        pass


def read_recent_logs(n: int = 20) -> List[str]:
    """Read the last n log entries."""
    log_path = get_log_path()

    if not log_path.exists():
        return []

    try:
        lines = log_path.read_text(encoding="utf-8").splitlines()
        return lines[-n:]
    except Exception:
        return []
