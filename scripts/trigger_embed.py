#!/usr/bin/env python3
"""
Lightweight trigger to re-embed index trees after filesystem writes.

Usage:
  python3 scripts/trigger_embed.py [--primitives] [--memory] [--all]

Called automatically by log_memory.py, consolidate_memories.py, and
any script that modifies primitives or memory hierarchy files.

Runs embed_primitives.py in the background to avoid blocking callers.
Uses a debounce lock to prevent rapid re-runs (5s cooldown).
"""

import os
import sys
import time
import subprocess
from pathlib import Path

WORKSPACE = Path(os.environ.get("WORKSPACE", Path.home() / ".openclaw" / "workspace"))
LOCK_FILE = WORKSPACE / ".embed_trigger.lock"
DEBOUNCE_SECONDS = 5


def should_run() -> bool:
    """Check debounce lock — skip if last run was < DEBOUNCE_SECONDS ago."""
    if LOCK_FILE.exists():
        try:
            last_run = LOCK_FILE.stat().st_mtime
            if time.time() - last_run < DEBOUNCE_SECONDS:
                return False
        except OSError:
            pass
    return True


def touch_lock():
    """Update lock file timestamp."""
    LOCK_FILE.touch()


def trigger(background: bool = True):
    """Run embed_primitives.py, optionally in background."""
    if not should_run():
        return

    touch_lock()
    script = WORKSPACE / "scripts" / "embed_primitives.py"
    if not script.exists():
        return

    cmd = [sys.executable, str(script)]

    if background:
        # Fire and forget — don't block the caller
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(WORKSPACE),
        )
    else:
        subprocess.run(cmd, cwd=str(WORKSPACE), capture_output=True)


def main():
    bg = "--foreground" not in sys.argv
    trigger(background=bg)


if __name__ == "__main__":
    main()
