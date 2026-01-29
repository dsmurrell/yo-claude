"""Configuration management for yo-claude."""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Use stdlib tomllib on 3.11+, fall back to tomli on older versions
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass
class Config:
    """Configuration for yo-claude."""

    # How often to check if a yo is needed (minutes)
    check_interval: int = 10

    # Send a yo if this many minutes have passed since the last one
    # Default: 5 hours 1 minute (just over the ~5 hour session window)
    yo_interval: int = 301

    # Path to claude CLI (None = auto-detect)
    claude_path: Optional[str] = None


def get_data_dir() -> Path:
    """Get the yo-claude data directory, creating it if needed."""
    home = Path.home()
    data_dir = home / ".yo-claude"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_config_path() -> Path:
    """Get the path to the config file."""
    return get_data_dir() / "config.toml"


def get_state_path() -> Path:
    """Get the path to the state file."""
    return get_data_dir() / "state.json"


def get_log_path() -> Path:
    """Get the path to the log file."""
    return get_data_dir() / "yo-claude.log"


def load_config() -> Config:
    """Load configuration from file, using defaults for missing values."""
    config_path = get_config_path()
    config = Config()

    if not config_path.exists():
        return config

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        if "check_interval" in data:
            config.check_interval = int(data["check_interval"])
        if "yo_interval" in data:
            config.yo_interval = int(data["yo_interval"])
        if "claude_path" in data:
            config.claude_path = str(data["claude_path"])

    except Exception:
        # If config is malformed, use defaults
        pass

    return config


def create_default_config(force: bool = False) -> None:
    """Create a default config file with comments explaining each option."""
    config_path = get_config_path()

    if config_path.exists() and not force:
        return

    default_config = """# yo-claude configuration
# All values are optional - defaults are shown below

# How often to check if a yo is needed (minutes)
check_interval = 10

# Send a yo if this many minutes have passed since the last one
# Default is 301 (5 hours 1 minute) - just over the ~5 hour session window
yo_interval = 301

# Path to claude CLI (auto-detected if not set)
# claude_path = "/usr/local/bin/claude"
"""

    config_path.write_text(default_config, encoding="utf-8")
