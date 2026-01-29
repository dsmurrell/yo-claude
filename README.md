# yo-claude

**Start your Claude session refresh early to avoid mid-work interruptions**

A tiny tool that says "yo" to Claude every 5 hours so your rate limit resets while you're not working.

## What this does

Claude has a session-based rate limit with a ~5 hour window. If you're deep in flow when the timer expires, you get interrupted. Annoying.

**The problem:** Your session timer only starts when you send your first message:

![Session not started](has-not-started.png)

**The solution:** yo-claude sends a "yo" every 5 hours to start the timer early:

![Session timer running](starts-after-first-send.png)

This way, the cooldown happens during idle time instead of interrupting your deep work.

## What this doesn't do

- Increase your quota
- Guarantee uninterrupted sessions
- Break any rules

It just automates something you could do manually.

## Requirements

- Python 3.9+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated

## Installation

```bash
pip install yo-claude
```

Or with pipx (recommended):

```bash
pipx install yo-claude
```

## Usage

### Quick start

```bash
# Check if yo needed and send if so
yo-claude

# Force send a yo regardless of timer
yo-claude send

# Check status
yo-claude status
```

### Run automatically in the background

```bash
# Install the background scheduler
yo-claude install

# Check it's working
yo-claude status

# Remove when you don't want it anymore
yo-claude uninstall
```

This uses your OS's native scheduler:
- **macOS**: LaunchAgent
- **Linux**: systemd user timer
- **Windows**: Task Scheduler

All user-level, no root/admin required, easily removable.

### View logs

```bash
yo-claude logs
yo-claude logs -n 50  # last 50 entries
```

## Configuration

Config file: `~/.yo-claude/config.toml`

Create one with defaults:

```bash
yo-claude config --create
```

Options:

```toml
# How often to check if a yo is needed (minutes)
check_interval = 10

# Send a yo if this many minutes have passed since the last one
# Default is 301 (5 hours 1 minute) - just over the ~5 hour session window
yo_interval = 301

# Path to claude CLI (auto-detected if not set)
# claude_path = "/usr/local/bin/claude"
```

### Why check every 10 minutes?

If the scheduler only woke every 5 hours and your computer slept through it, you'd miss the window entirely. By checking frequently, you catch up quickly after waking - the first check sees "it's been 6 hours since last yo" and sends immediately.

## How it works

1. Scheduler wakes every 10 minutes
2. Checks: has it been 5+ hours since last yo?
3. If yes → sends `claude -p "yo"` and records the time
4. If no → does nothing
5. Goes back to sleep

## Files

Everything lives in `~/.yo-claude/`:

```
~/.yo-claude/
  config.toml    # Your configuration (optional)
  state.json     # Last yo timestamp
  yo-claude.log  # What happened and when
```

## Cost

Each "yo" is ~15-20 tokens. You send ~5 per day. That's less than 100 tokens/day - completely negligible.

## Manual setup (if you prefer)

If you'd rather use your own scheduler:

```bash
# The only command you need to run periodically
yo-claude run
```

Or skip the package entirely:

```bash
claude -p "yo"
```

That's literally all this tool automates.

## Uninstalling

```bash
# Remove the scheduler
yo-claude uninstall

# Uninstall the package
pip uninstall yo-claude

# Optionally remove config/state
rm -rf ~/.yo-claude
```

## Platform notes

### macOS

The scheduler appears in System Settings → General → Login Items as "python3.x - Item from unidentified developer". This is normal for Python-based LaunchAgents.

`yo-claude install` automatically detects and saves your claude path, so it works even if you installed Claude Code via nvm or Homebrew.

### Linux

Uses systemd user timers. Should work out of the box, but **not yet tested**. If you're on Linux, please test and report issues or submit fixes!

### Windows

Uses Task Scheduler. Should work, but **not yet tested**. If you're on Windows, please test and report issues or submit fixes!

## License

MIT

## FAQ

**Does this eat into my quota?**

Barely. ~5 yos per day at ~20 tokens each = ~100 tokens. Less than a single short question.

**What if I also use Claude via the web?**

Both count toward the same session. Your yo will either start a fresh session (if the previous expired) or do nothing harmful (if a session is already active). Either way, ~20 tokens.

**Is this cheating?**

No. You're just automating the act of sending a trivial message. The same limits apply.

**Why Python?**

Readable, auditable, runs everywhere. The entire codebase is ~250 lines.

**What if Claude changes their session window?**

The `yo_interval` is configurable. Update your config if needed.

**What if my computer was asleep?**

When it wakes, the scheduler runs within 10 minutes, sees that 5+ hours have passed, and sends a yo. You're back in sync.

**The scheduler can't find claude but it works in my terminal?**

`yo-claude install` should auto-detect your claude path. If it didn't work, set it manually in `~/.yo-claude/config.toml`:

```toml
claude_path = "/full/path/to/claude"
```

Find your path with `which claude`, then run `yo-claude uninstall && yo-claude install`.
