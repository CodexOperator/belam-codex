#!/usr/bin/env python3
"""
setup_memory_crons.py — Install memory system cron jobs.

Installs or updates the cron entries for the hierarchical memory system:
  - Daily consolidation + linking + file checks (00:05 UTC)
  - Weekly roll-up (Monday 03:00 UTC)
  - Monthly roll-up (1st of month 04:00 UTC)

Usage:
  python3 scripts/setup_memory_crons.py              # Install crons
  python3 scripts/setup_memory_crons.py --dry-run    # Preview only
  python3 scripts/setup_memory_crons.py --remove     # Remove memory crons
  python3 scripts/setup_memory_crons.py --status     # Show current crontab
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent

# Cron entries to manage
CRON_ENTRIES = [
    {
        "id": "openclaw-daily-memory",
        "schedule": "5 0 * * *",
        "command": f"cd {WORKSPACE} && python3 scripts/daily_agent_memory.py >> /tmp/openclaw_daily_memory.log 2>&1",
        "description": "Daily memory consolidation + linking + file checks",
    },
    {
        "id": "openclaw-weekly-memory",
        "schedule": "0 3 * * 1",
        "command": f"cd {WORKSPACE} && python3 scripts/memory_weekly_consolidation.py >> /tmp/openclaw_weekly_memory.log 2>&1",
        "description": "Weekly memory roll-up (Monday 03:00 UTC)",
    },
    {
        "id": "openclaw-monthly-memory",
        "schedule": "0 4 1 * *",
        "command": f"cd {WORKSPACE} && python3 scripts/memory_monthly_consolidation.py >> /tmp/openclaw_monthly_memory.log 2>&1",
        "description": "Monthly memory roll-up (1st of month 04:00 UTC)",
    },
]


def get_current_crontab() -> str:
    """Read the current crontab for this user."""
    result = subprocess.run(
        ["crontab", "-l"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout
    # No crontab yet
    return ""


def set_crontab(content: str) -> bool:
    """Write a new crontab."""
    result = subprocess.run(
        ["crontab", "-"],
        input=content,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def format_cron_line(entry: dict) -> str:
    """Format a single cron entry as a crontab line."""
    return f"# {entry['id']}: {entry['description']}\n{entry['schedule']} {entry['command']}"


def install_crons(dry_run: bool = False) -> int:
    """Install or update memory cron entries. Returns count of changes."""
    current = get_current_crontab()
    lines = current.splitlines(keepends=True) if current else []

    added = 0
    updated = 0

    for entry in CRON_ENTRIES:
        cron_id = entry["id"]
        new_line = format_cron_line(entry)

        # Check if this cron already exists (by ID)
        id_pattern = re.compile(rf"# {re.escape(cron_id)}:")

        existing_block_start = None
        for i, line in enumerate(lines):
            if id_pattern.match(line.rstrip()):
                existing_block_start = i
                break

        if existing_block_start is not None:
            # Check if command has changed
            old_comment = lines[existing_block_start].rstrip()
            old_command = lines[existing_block_start + 1].rstrip() if existing_block_start + 1 < len(lines) else ""

            expected_comment = f"# {cron_id}: {entry['description']}"
            expected_command = f"{entry['schedule']} {entry['command']}"

            if old_command == expected_command:
                print(f"  ✓ Already current: {cron_id}")
                continue

            # Replace the existing block
            if dry_run:
                print(f"  [DRY RUN] Would update: {cron_id}")
                print(f"    Old: {old_command[:80]}...")
                print(f"    New: {expected_command[:80]}...")
            else:
                new_lines = list(lines)
                new_lines[existing_block_start] = expected_comment + "\n"
                if existing_block_start + 1 < len(new_lines):
                    new_lines[existing_block_start + 1] = expected_command + "\n"
                lines = new_lines
                print(f"  ✓ Updated: {cron_id}")
            updated += 1
        else:
            # Add new entry
            if dry_run:
                print(f"  [DRY RUN] Would add: {cron_id}")
                print(f"    {entry['schedule']} {entry['command'][:60]}...")
            else:
                # Ensure there's a newline before our block
                if lines and not lines[-1].endswith("\n"):
                    lines.append("\n")
                elif lines and lines[-1].strip():
                    lines.append("\n")
                lines.append(new_line + "\n")
                print(f"  ✓ Added: {cron_id}")
            added += 1

    if not dry_run and (added > 0 or updated > 0):
        new_crontab = "".join(lines)
        if set_crontab(new_crontab):
            print(f"\n✓ Crontab updated ({added} added, {updated} updated)")
        else:
            print(f"\n✗ Failed to update crontab")
            return -1

    return added + updated


def remove_crons(dry_run: bool = False) -> int:
    """Remove all memory cron entries. Returns count removed."""
    current = get_current_crontab()
    if not current:
        print("  No crontab found.")
        return 0

    lines = current.splitlines(keepends=True)
    new_lines = []
    removed = 0
    skip_next = False

    cron_ids = {entry["id"] for entry in CRON_ENTRIES}
    id_patterns = [re.compile(rf"# {re.escape(cid)}:") for cid in cron_ids]

    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if this line is a comment for one of our cron IDs
        is_our_comment = any(p.match(line.rstrip()) for p in id_patterns)

        if is_our_comment:
            # Remove this line (comment) and next line (the actual cron)
            if dry_run:
                print(f"  [DRY RUN] Would remove: {line.rstrip()}")
                if i + 1 < len(lines):
                    print(f"  [DRY RUN] Would remove: {lines[i+1].rstrip()}")
            removed += 1
            i += 2  # Skip comment + cron line
            # Skip blank line after if present
            if i < len(lines) and not lines[i].strip():
                i += 1
            continue

        new_lines.append(line)
        i += 1

    if not dry_run and removed > 0:
        new_crontab = "".join(new_lines)
        if set_crontab(new_crontab):
            print(f"✓ Removed {removed} cron entries")
        else:
            print(f"✗ Failed to update crontab")
            return -1

    return removed


def show_status():
    """Print current crontab with memory entries highlighted."""
    current = get_current_crontab()
    if not current:
        print("  No crontab configured.")
        return

    print("Current crontab:")
    print("─" * 60)

    cron_ids = {entry["id"] for entry in CRON_ENTRIES}
    id_patterns = {cid: re.compile(rf"# {re.escape(cid)}:") for cid in cron_ids}

    for line in current.splitlines():
        # Highlight our entries
        is_ours = any(p.match(line) for p in id_patterns.values())
        if is_ours:
            print(f"  [MEMORY] {line}")
        else:
            print(f"           {line}")

    print("─" * 60)

    # Show which of our entries exist
    print("\nMemory cron status:")
    for entry in CRON_ENTRIES:
        pattern = re.compile(rf"# {re.escape(entry['id'])}:")
        exists = any(pattern.match(line) for line in current.splitlines())
        status = "✓ installed" if exists else "✗ missing"
        print(f"  {status}: {entry['id']} ({entry['schedule']})")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Install memory system cron jobs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Cron entries to be managed:
  Daily (00:05 UTC):    daily_agent_memory.py
  Weekly (Mon 03:00):   memory_weekly_consolidation.py
  Monthly (1st 04:00):  memory_monthly_consolidation.py

Workspace: {WORKSPACE}

Examples:
  python3 scripts/setup_memory_crons.py
  python3 scripts/setup_memory_crons.py --dry-run
  python3 scripts/setup_memory_crons.py --remove
  python3 scripts/setup_memory_crons.py --status
        """,
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no changes.")
    parser.add_argument("--remove", action="store_true", help="Remove all memory cron entries.")
    parser.add_argument("--status", action="store_true", help="Show current crontab status.")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.remove:
        print("🗑️  Removing memory cron entries...")
        if args.dry_run:
            print("   Mode: DRY RUN\n")
        n = remove_crons(dry_run=args.dry_run)
        if n >= 0:
            print(f"\n{'[DRY RUN] ' if args.dry_run else ''}✅ Removed {n} cron entries")
        return

    print("⏰ Setting up memory system cron jobs...")
    if args.dry_run:
        print("   Mode: DRY RUN\n")

    print("\nEntries to install:")
    for entry in CRON_ENTRIES:
        print(f"  {entry['schedule']:15s}  {entry['description']}")
    print()

    n = install_crons(dry_run=args.dry_run)

    if n == 0:
        print(f"\n✅ All cron entries already current — no changes needed")
    elif n > 0:
        print(f"\n{'[DRY RUN] ' if args.dry_run else ''}✅ Cron setup complete ({n} changes)")
    else:
        print(f"\n✗ Cron setup failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
