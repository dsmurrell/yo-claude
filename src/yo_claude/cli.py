"""Command-line interface for yo-claude."""

import argparse
import sys
from typing import Optional, List

from . import __version__
from .config import load_config, create_default_config, get_config_path
from .core import send_yo, get_status
from .scheduler import install, uninstall, get_scheduler_status
from .logging import read_recent_logs


def cmd_run(args) -> int:
    """Default command - check if yo needed and send if so."""
    config = load_config()
    success, message = send_yo(config, force=False)
    print(message)
    return 0 if success else 1


def cmd_send(args) -> int:
    """Force send a yo regardless of timer."""
    config = load_config()
    success, message = send_yo(config, force=True)
    print(message)
    return 0 if success else 1


def cmd_status(args) -> int:
    """Show current status."""
    config = load_config()
    status = get_status(config)
    scheduler = get_scheduler_status()

    print("yo-claude status")
    print("=" * 40)

    # Claude CLI
    if status["claude_cli_found"]:
        print(f"Claude CLI:     Found at {status['claude_cli_path']}")
    else:
        print("Claude CLI:     NOT FOUND")

    # Last yo
    if status["last_yo_sent_at_human"]:
        print(f"Last yo sent:   {status['last_yo_sent_at_human']}")
        print(f"                ({status['minutes_since_last_yo']} minutes ago)")
    else:
        print("Last yo sent:   Never")

    # Next yo
    if status["minutes_until_next_yo"] is not None:
        print(f"Next yo in:     {status['minutes_until_next_yo']} minutes")
    else:
        print("Next yo in:     Now (ready to send)")

    # Intervals
    yo_hours = status["yo_interval"] // 60
    yo_mins = status["yo_interval"] % 60
    print(f"Yo interval:    {yo_hours}h {yo_mins}m")
    print(f"Check interval: {status['check_interval']} minutes")

    # Scheduler
    print()
    if scheduler["installed"]:
        print(f"Scheduler:      Installed ({scheduler['platform']})")
        print(f"                {scheduler['details']}")
    else:
        print("Scheduler:      Not installed")
        print("                Run 'yo-claude install' to enable background running")

    return 0


def cmd_config(args) -> int:
    """Show config information."""
    config = load_config()
    config_path = get_config_path()

    print(f"Config file: {config_path}")
    print()

    if not config_path.exists():
        print("No config file found. Using defaults.")
        print("Run 'yo-claude config --create' to create one.")
    else:
        print("Current configuration:")
        print(f"  check_interval:   {config.check_interval} minutes")
        yo_hours = config.yo_interval // 60
        yo_mins = config.yo_interval % 60
        print(f"  yo_interval:      {config.yo_interval} minutes ({yo_hours}h {yo_mins}m)")
        if config.claude_path:
            print(f"  claude_path:      {config.claude_path}")
        else:
            print("  claude_path:      auto-detect")

    return 0


def cmd_config_create(args) -> int:
    """Create default config file."""
    config_path = get_config_path()

    if config_path.exists() and not args.force:
        print(f"Config file already exists at {config_path}")
        print("Use --force to overwrite")
        return 1

    create_default_config(force=args.force)
    print(f"Created config file at {config_path}")
    return 0


def cmd_install(args) -> int:
    """Install the background scheduler."""
    import shutil
    from .config import get_config_path

    config = load_config()

    # Auto-detect and save claude path if not already configured
    # This captures the path from the user's current shell environment
    if not config.claude_path:
        claude_path = shutil.which("claude")
        if claude_path:
            config_path = get_config_path()
            if config_path.exists():
                # Append to existing config
                with open(config_path, "a", encoding="utf-8") as f:
                    f.write(f'\nclaude_path = "{claude_path}"\n')
            else:
                # Create config with claude_path
                with open(config_path, "w", encoding="utf-8") as f:
                    f.write(f'claude_path = "{claude_path}"\n')
            print(f"Saved claude path: {claude_path}")
            # Reload config with new path
            config = load_config()
        else:
            print("WARNING: Could not find claude CLI in PATH.")
            print("The scheduler may fail. Set claude_path in ~/.yo-claude/config.toml")
            print()

    success, message = install(config)
    print(message)

    if success:
        yo_hours = config.yo_interval // 60
        yo_mins = config.yo_interval % 60
        print()
        print(f"yo-claude will check every {config.check_interval} minutes")
        print(f"and send a yo every {yo_hours}h {yo_mins}m.")
        print("To check status: yo-claude status")
        print("To remove:       yo-claude uninstall")

    return 0 if success else 1


def cmd_uninstall(args) -> int:
    """Remove the background scheduler."""
    success, message = uninstall()
    print(message)
    return 0 if success else 1


def cmd_logs(args) -> int:
    """Show recent log entries."""
    logs = read_recent_logs(args.lines)

    if not logs:
        print("No log entries found.")
        return 0

    for line in logs:
        print(line)

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="yo-claude", description="Start your Claude session refresh early to avoid mid-work interruptions"
    )
    parser.add_argument("-v", "--version", action="version", version=f"yo-claude {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    # run (default when no subcommand)
    run_parser = subparsers.add_parser("run", help="Check if yo needed and send if so (default)")
    run_parser.set_defaults(func=cmd_run)

    # send
    send_parser = subparsers.add_parser("send", help="Force send a yo regardless of timer")
    send_parser.set_defaults(func=cmd_send)

    # status
    status_parser = subparsers.add_parser("status", help="Show current status")
    status_parser.set_defaults(func=cmd_status)

    # config
    config_parser = subparsers.add_parser("config", help="Show config file location and values")
    config_parser.add_argument("--create", action="store_true", help="Create default config file")
    config_parser.add_argument("--force", action="store_true", help="Overwrite existing config file")
    config_parser.set_defaults(func=lambda args: cmd_config_create(args) if args.create else cmd_config(args))

    # install
    install_parser = subparsers.add_parser("install", help="Install background scheduler")
    install_parser.set_defaults(func=cmd_install)

    # uninstall
    uninstall_parser = subparsers.add_parser("uninstall", help="Remove background scheduler")
    uninstall_parser.set_defaults(func=cmd_uninstall)

    # logs
    logs_parser = subparsers.add_parser("logs", help="Show recent log entries")
    logs_parser.add_argument("-n", "--lines", type=int, default=20, help="Number of lines to show (default: 20)")
    logs_parser.set_defaults(func=cmd_logs)

    args = parser.parse_args(argv)

    # Default to 'run' if no subcommand given
    if args.command is None:
        return cmd_run(args)

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
