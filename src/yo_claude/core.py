"""Core logic for yo-claude."""

import json
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from .config import Config, get_state_path
from .logging import log


def load_state() -> dict:
    """Load the state file."""
    state_path = get_state_path()

    if not state_path.exists():
        return {}

    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict) -> None:
    """Save the state file atomically."""
    state_path = get_state_path()
    tmp_path = state_path.with_suffix(".tmp")

    tmp_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp_path.replace(state_path)


def find_claude_cli(config: Config) -> Optional[str]:
    """Find the claude CLI executable."""
    if config.claude_path:
        if Path(config.claude_path).exists():
            return config.claude_path
        return None

    # Auto-detect
    path = shutil.which("claude")
    return path


def should_send_yo(config: Config) -> Tuple[bool, str]:
    """
    Check if enough time has passed since last yo.

    Returns (should_send, reason).
    """
    state = load_state()
    last_sent = state.get("last_yo_sent_at")

    # If never sent, send now
    if last_sent is None:
        return True, "No previous yo recorded"

    # Check if yo_interval has passed
    now = int(time.time())
    threshold_seconds = config.yo_interval * 60
    elapsed = now - last_sent
    elapsed_mins = elapsed // 60

    if elapsed >= threshold_seconds:
        return True, f"Time to send yo ({elapsed_mins} minutes since last)"

    remaining = (threshold_seconds - elapsed) // 60
    return False, f"Waiting ({remaining} minutes until next yo)"


def send_yo(config: Config, force: bool = False) -> Tuple[bool, str]:
    """
    Send a yo to Claude if needed.

    Args:
        config: Configuration object
        force: If True, send regardless of timer

    Returns (success, message).
    """
    # Check if we should send
    if not force:
        should_send, reason = should_send_yo(config)
        if not should_send:
            return True, reason

    # Find claude CLI
    claude_path = find_claude_cli(config)
    if not claude_path:
        msg = "Could not find claude CLI. Install Claude Code or set claude_path in config."
        log(f"ERROR: {msg}")
        return False, msg

    # Send the yo
    try:
        result = subprocess.run([claude_path, "-p", "yo"], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            # Success - update state
            response = result.stdout.strip()
            state = load_state()
            state["last_yo_sent_at"] = int(time.time())
            state["last_response"] = response[:200]  # Keep first 200 chars
            save_state(state)

            msg = f"Sent yo successfully. Response: {response[:100]}"
            log(msg)
            return True, msg
        else:
            msg = f"claude CLI returned error: {result.stderr.strip() or result.stdout.strip()}"
            log(f"ERROR: {msg}")
            return False, msg

    except subprocess.TimeoutExpired:
        msg = "claude CLI timed out after 30 seconds"
        log(f"ERROR: {msg}")
        return False, msg
    except Exception as e:
        msg = f"Failed to run claude CLI: {e}"
        log(f"ERROR: {msg}")
        return False, msg


def get_status(config: Config) -> dict:
    """Get current status information."""
    state = load_state()
    last_sent = state.get("last_yo_sent_at")

    now = int(time.time())
    threshold_seconds = config.yo_interval * 60

    status = {
        "check_interval": config.check_interval,
        "yo_interval": config.yo_interval,
        "last_yo_sent_at": last_sent,
        "last_yo_sent_at_human": None,
        "minutes_since_last_yo": None,
        "minutes_until_next_yo": None,
        "claude_cli_found": find_claude_cli(config) is not None,
        "claude_cli_path": find_claude_cli(config),
    }

    if last_sent:
        status["last_yo_sent_at_human"] = datetime.fromtimestamp(last_sent).strftime("%Y-%m-%d %H:%M:%S")
        elapsed = now - last_sent
        status["minutes_since_last_yo"] = elapsed // 60

        if elapsed < threshold_seconds:
            status["minutes_until_next_yo"] = (threshold_seconds - elapsed) // 60

    return status
