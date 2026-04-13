#!/usr/bin/env python3
"""
daily_agent_memory.py — Daily cross-agent memory consolidation cron job.

Runs at midnight UTC. For each agent workspace:
  a) Consolidates that day's raw entries into the daily log
  b) Reads the daily log and extracts a summary
  c) Appends a per-agent section to the MAIN daily log
  d) Archives daily logs older than 7 days into memory/archive/YYYY-MM/
  e) Creates a fresh daily log file for the next day

Usage:
  python3 scripts/daily_agent_memory.py           # Run for today
  python3 scripts/daily_agent_memory.py --date 2026-03-17
  python3 scripts/daily_agent_memory.py --dry-run  # Preview only
"""

import argparse
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Canonical workspace paths
AGENT_WORKSPACES = {
    "main":      Path(os.path.expanduser("~/.openclaw/workspace")),
    "architect": Path(os.path.expanduser("~/.openclaw/workspace-architect")),
    "critic":    Path(os.path.expanduser("~/.openclaw/workspace-critic")),
    "builder":   Path(os.path.expanduser("~/.openclaw/workspace-builder")),
}

MAIN_WORKSPACE = AGENT_WORKSPACES["main"]
SUB_AGENTS = {k: v for k, v in AGENT_WORKSPACES.items() if k != "main"}

SCRIPTS_DIR = MAIN_WORKSPACE / "scripts"

ARCHIVE_KEEP_DAYS = 7


def _run_script(script_name: str, extra_args: list[str], dry_run: bool) -> int:
    """Run a script from the scripts/ directory. Returns returncode."""
    import subprocess
    script = str(SCRIPTS_DIR / script_name)
    cmd = [sys.executable, script] + extra_args
    if dry_run:
        cmd.append("--dry-run")
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def run_consolidate(workspace: Path, date_str: str, dry_run: bool, label: str) -> int:
    """Run consolidate_memories for a workspace. Returns count consolidated."""
    import subprocess
    script = str(SCRIPTS_DIR / "consolidate_memories.py")
    cmd = [sys.executable, script, "--workspace", str(workspace), "--date", date_str]
    if dry_run:
        cmd.append("--dry-run")
    print(f"\n── Consolidating {label} ──")
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def extract_bullet_points(text: str, max_bullets: int = 8) -> list[str]:
    """
    Extract meaningful bullet points from a daily log text.
    Looks for lines starting with '-', '•', or category headers with content.
    """
    bullets = []
    # Try to get bullets from the consolidated entries section first
    in_consolidated = False
    for line in text.splitlines():
        line = line.strip()
        if "## Consolidated Entries" in line:
            in_consolidated = True
            continue
        if in_consolidated:
            # Skip category headers and empty lines
            if line.startswith("###") or not line or line == "---":
                continue
            # Grab bullet lines
            if line.startswith("- ") or line.startswith("• "):
                # Strip formatting like **[★★★☆☆]**
                clean = re.sub(r"\*\*\[[\★☆]+\]\*\* ", "", line)
                # Strip source refs like *(source: ...)*
                clean = re.sub(r"\*\(source:[^)]+\)\*", "", clean).strip()
                # Strip importance markers
                clean = re.sub(r"\*tags:[^*]+\*", "", clean).strip()
                if len(clean) > 10:
                    bullets.append(clean)
            if len(bullets) >= max_bullets:
                break

    # Fallback: grab content lines from raw log entries
    if not bullets:
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("*") or line == "---":
                continue
            if len(line) > 20 and not line.startswith("|"):
                bullets.append(f"- {line[:120]}")
            if len(bullets) >= max_bullets:
                break

    return bullets[:max_bullets]


def read_daily_log(workspace: Path, date_str: str) -> str | None:
    """Read a daily log file. Returns None if not found."""
    log_path = workspace / "memory" / f"{date_str}.md"
    if log_path.exists():
        return log_path.read_text()
    return None


def generate_agent_summary(agent_name: str, workspace: Path, date_str: str) -> str | None:
    """
    Generate a summary section for one agent to be appended to the main daily log.
    Returns None if no content found.
    """
    log_text = read_daily_log(workspace, date_str)
    if not log_text or log_text.strip() == f"# Memory Log — {date_str}":
        return None

    bullets = extract_bullet_points(log_text)
    if not bullets:
        return None

    agent_label = agent_name.title()
    lines = [f"\n## Agent: {agent_label} — {date_str}\n"]
    for b in bullets:
        lines.append(b)
    lines.append("")
    return "\n".join(lines)


def append_to_main_daily_log(date_str: str, summaries: list[str], dry_run: bool):
    """Append per-agent summary sections to the MAIN daily log."""
    main_memory_dir = MAIN_WORKSPACE / "memory"
    daily_log = main_memory_dir / f"{date_str}.md"

    if not summaries:
        print("\nNo agent summaries to append to main log.")
        return

    # Build the block to append
    ts_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = f"\n---\n\n## Cross-Agent Summary — {date_str}\n\n*Consolidated at {ts_now}*\n"
    content_to_append = header + "\n".join(summaries) + "\n---\n"

    if dry_run:
        print("\n=== DRY RUN: Would append to main daily log ===")
        print(content_to_append)
        return

    main_memory_dir.mkdir(parents=True, exist_ok=True)
    if not daily_log.exists():
        daily_log.write_text(f"# Memory Log — {date_str}\n\n")

    with daily_log.open("a") as f:
        f.write(content_to_append)

    print(f"\n✓ Appended {len(summaries)} agent summaries to main daily log: {daily_log}")


def archive_old_logs(workspace: Path, cutoff: datetime, dry_run: bool, label: str) -> int:
    """Archive daily log files older than cutoff into memory/archive/YYYY-MM/."""
    memory_dir = workspace / "memory"
    archived = 0

    if not memory_dir.exists():
        return 0

    for f in memory_dir.glob("????-??-??.md"):
        try:
            file_date = datetime.strptime(f.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if file_date < cutoff:
            yyyy_mm = file_date.strftime("%Y-%m")
            dest_dir = memory_dir / "archive" / yyyy_mm
            if dry_run:
                print(f"  [DRY RUN] [{label}] Would archive: memory/{f.name} → memory/archive/{yyyy_mm}/")
            else:
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(dest_dir / f.name))
            archived += 1

    return archived


def create_next_day_log(workspace: Path, next_date_str: str, dry_run: bool, label: str):
    """Create an empty daily log for next_date_str if it doesn't exist."""
    memory_dir = workspace / "memory"
    next_log = memory_dir / f"{next_date_str}.md"

    if next_log.exists():
        return

    if dry_run:
        print(f"  [DRY RUN] [{label}] Would create: memory/{next_date_str}.md")
        return

    memory_dir.mkdir(parents=True, exist_ok=True)
    next_log.write_text(f"# Memory Log — {next_date_str}\n\n")
    print(f"  [{label}] Created fresh log: memory/{next_date_str}.md")


def main():
    parser = argparse.ArgumentParser(
        description="Daily cross-agent memory consolidation — runs at midnight UTC via cron.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/daily_agent_memory.py
  python3 scripts/daily_agent_memory.py --date 2026-03-17
  python3 scripts/daily_agent_memory.py --dry-run
        """,
    )
    parser.add_argument(
        "--date",
        help="Date to process (YYYY-MM-DD, default: today UTC)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would happen without writing files",
    )

    args = parser.parse_args()
    now_utc = datetime.now(timezone.utc)
    date_str = args.date or now_utc.strftime("%Y-%m-%d")
    next_date_str = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    cutoff = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc) - timedelta(days=ARCHIVE_KEEP_DAYS)

    print(f"🌅 Daily Agent Memory — {date_str}")
    if args.dry_run:
        print("   Mode: DRY RUN\n")

    # ── Step A: Consolidate each agent's entries ─────────────────────────────
    print(f"\n📋 Step A: Consolidating entries for {date_str}")
    for agent_name, workspace in AGENT_WORKSPACES.items():
        run_consolidate(workspace, date_str, args.dry_run, agent_name)

    # ── Step A2: Run daily linker (wiki + transcript + recent memory links) ───
    print(f"\n🔗 Step A2: Running daily memory linker")
    _run_script("memory_daily_linker.py", ["--date", date_str], args.dry_run)

    # ── Step A3: Run file update checker ─────────────────────────────────────
    print(f"\n🔍 Step A3: Running file update checker")
    _run_script("memory_file_update_checker.py", ["--date", date_str], args.dry_run)

    # ── Step B+C: Read each sub-agent's log, generate summary for main ────────
    print(f"\n📝 Step B: Reading sub-agent logs and generating main summaries")
    summaries = []
    for agent_name, workspace in SUB_AGENTS.items():
        summary = generate_agent_summary(agent_name, workspace, date_str)
        if summary:
            print(f"  ✓ {agent_name}: extracted summary")
            summaries.append(summary)
        else:
            print(f"  ○ {agent_name}: no content for {date_str}")

    # ── Step C: Append summaries to main daily log ────────────────────────────
    print(f"\n📎 Step C: Appending to main daily log")
    append_to_main_daily_log(date_str, summaries, args.dry_run)

    # ── Step D: Archive old logs ──────────────────────────────────────────────
    print(f"\n📦 Step D: Archiving logs older than {ARCHIVE_KEEP_DAYS} days (before {cutoff.strftime('%Y-%m-%d')})")
    total_archived = 0
    for agent_name, workspace in AGENT_WORKSPACES.items():
        n = archive_old_logs(workspace, cutoff, args.dry_run, agent_name)
        if n:
            print(f"  [{agent_name}] Archived {n} file(s)")
        total_archived += n
    print(f"  Total archived: {total_archived}")

    # ── Step E: Create fresh daily logs for next day ──────────────────────────
    print(f"\n🌄 Step E: Creating next-day log files ({next_date_str})")
    for agent_name, workspace in AGENT_WORKSPACES.items():
        create_next_day_log(workspace, next_date_str, args.dry_run, agent_name)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}✅ Daily agent memory complete for {date_str}")


if __name__ == "__main__":
    main()
