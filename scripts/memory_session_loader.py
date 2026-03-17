#!/usr/bin/env python3
"""
memory_session_loader.py — Session startup memory context loader.

Loads appropriate memory context for the current session:
  - Always: today's daily memory (creates empty if doesn't exist)
  - Always: current week's weekly summary (if exists)
  - Always: current month's monthly summary (if exists)
  - Prints a brief "memory context loaded" summary
  - Other levels available on-demand but not loaded

Usage:
  python3 scripts/memory_session_loader.py          # Load current session memory
  python3 scripts/memory_session_loader.py --quiet  # Minimal output, just return content
  python3 scripts/memory_session_loader.py --json   # Output as JSON for programmatic use
  python3 scripts/memory_session_loader.py --date 2026-03-17
"""

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
MEMORY_DIR = WORKSPACE / "memory"
WEEKLY_DIR = MEMORY_DIR / "weekly"
MONTHLY_DIR = MEMORY_DIR / "monthly"
QUARTERLY_DIR = MEMORY_DIR / "quarterly"
YEARLY_DIR = MEMORY_DIR / "yearly"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def week_str_for_date(d: datetime) -> str:
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def month_str_for_date(d: datetime) -> str:
    return d.strftime("%Y-%m")


def count_entries(content: str) -> int:
    """Count the number of bullet entries in a memory file."""
    return len(re.findall(r"^- \*\*\[", content, re.MULTILINE))


def extract_summary_lines(content: str, max_lines: int = 5) -> list[str]:
    """Extract the most important lines from a memory file for the summary."""
    lines = []

    # Try consolidated entries section first (highest importance entries)
    in_consolidated = False
    imp4_lines = []
    imp3_lines = []

    for line in content.splitlines():
        if "## Consolidated Entries" in line:
            in_consolidated = True
            continue

        if in_consolidated:
            entry_match = re.match(r"^- \*\*\[([★☆]+)\]\*\* (.+)", line)
            if entry_match:
                stars = entry_match.group(1).count("★")
                text = entry_match.group(2)[:80]
                if stars >= 4:
                    imp4_lines.append(f"  ★{stars} {text}")
                elif stars == 3:
                    imp3_lines.append(f"  ★{stars} {text}")

            if line.startswith("---") and in_consolidated:
                break

    lines = imp4_lines[:max_lines]
    if len(lines) < max_lines:
        lines.extend(imp3_lines[:max_lines - len(lines)])

    # Fallback: first section headers from the file
    if not lines:
        for line in content.splitlines():
            if line.startswith("## ") and not line.startswith("## Consolidated"):
                lines.append(f"  {line[3:60]}")
            if len(lines) >= max_lines:
                break

    return lines[:max_lines]


def format_file_summary(label: str, filepath: Path, content: str) -> str:
    """Format a one-line summary for a loaded memory file."""
    entry_count = count_entries(content)
    size_kb = len(content) / 1024
    rel = filepath.relative_to(WORKSPACE) if filepath.is_relative_to(WORKSPACE) else filepath
    return f"  {label}: {rel} ({size_kb:.1f} KB, {entry_count} entries)"


def find_available_levels(today: datetime) -> dict:
    """Return paths to all available memory files at all levels (for on-demand retrieval)."""
    available = {}

    # Quarterly files
    if QUARTERLY_DIR.exists():
        quarterly_files = sorted(QUARTERLY_DIR.glob("????-Q?.md"))
        if quarterly_files:
            available["quarterly"] = [str(f.relative_to(WORKSPACE)) for f in quarterly_files[-2:]]

    # Yearly files
    if YEARLY_DIR.exists():
        yearly_files = sorted(YEARLY_DIR.glob("????.md"))
        if yearly_files:
            available["yearly"] = [str(f.relative_to(WORKSPACE)) for f in yearly_files[-2:]]

    # Archive hints
    archive_dir = MEMORY_DIR / "archive"
    if archive_dir.exists():
        available["archive"] = str(archive_dir.relative_to(WORKSPACE))

    return available


# ─── Core loader ─────────────────────────────────────────────────────────────

def load_session_memory(date_str: str | None = None,
                         quiet: bool = False,
                         as_json: bool = False) -> dict:
    """
    Load memory context for a session.
    Returns dict with: {daily, weekly, monthly, summary, available}.
    """
    today = datetime.now(timezone.utc)
    if date_str:
        try:
            today = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"Error: Invalid date format '{date_str}'. Use YYYY-MM-DD.")
            return {}

    today_str = today.strftime("%Y-%m-%d")
    week_str = week_str_for_date(today)
    month_str = month_str_for_date(today)

    loaded = {}
    summaries = []

    # ── Daily memory (create if doesn't exist) ────────────────────────────────
    daily_file = MEMORY_DIR / f"{today_str}.md"
    if not daily_file.exists():
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        daily_file.write_text(f"# Memory Log — {today_str}\n\n")
        if not quiet:
            print(f"  📝 Created empty daily log: memory/{today_str}.md")

    daily_content = daily_file.read_text()
    loaded["daily"] = {"path": str(daily_file.relative_to(WORKSPACE)), "content": daily_content}
    summaries.append(format_file_summary("📅 Daily  ", daily_file, daily_content))

    # Extract top entries for context block
    daily_highlights = extract_summary_lines(daily_content)

    # ── Weekly summary (if exists) ────────────────────────────────────────────
    weekly_file = WEEKLY_DIR / f"{week_str}.md"
    if weekly_file.exists():
        weekly_content = weekly_file.read_text()
        loaded["weekly"] = {"path": str(weekly_file.relative_to(WORKSPACE)), "content": weekly_content}
        summaries.append(format_file_summary("📋 Weekly ", weekly_file, weekly_content))
    else:
        loaded["weekly"] = None
        summaries.append(f"  📋 Weekly : memory/weekly/{week_str}.md (not yet generated)")

    # ── Monthly summary (if exists) ───────────────────────────────────────────
    monthly_file = MONTHLY_DIR / f"{month_str}.md"
    if monthly_file.exists():
        monthly_content = monthly_file.read_text()
        loaded["monthly"] = {"path": str(monthly_file.relative_to(WORKSPACE)), "content": monthly_content}
        summaries.append(format_file_summary("🗓️  Monthly", monthly_file, monthly_content))
    else:
        loaded["monthly"] = None
        summaries.append(f"  🗓️  Monthly: memory/monthly/{month_str}.md (not yet generated)")

    # ── Available higher levels (not loaded, on-demand) ───────────────────────
    available = find_available_levels(today)
    loaded["available"] = available

    # ── Build context block ───────────────────────────────────────────────────
    context_lines = [
        f"# Session Memory Context — {today_str}",
        f"",
        f"*Loaded: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}*",
        f"",
        f"## Files Loaded",
        f"",
    ]
    context_lines.extend(summaries)
    context_lines.append("")

    if daily_highlights:
        context_lines.append("## Today's Key Entries")
        context_lines.append("")
        context_lines.extend(daily_highlights)
        context_lines.append("")

    if available:
        context_lines.append("## Higher Levels (On-Demand)")
        context_lines.append("")
        for level, paths in available.items():
            if isinstance(paths, list):
                context_lines.append(f"- **{level.title()}**: " + ", ".join(paths))
            else:
                context_lines.append(f"- **{level.title()}**: {paths}")
        context_lines.append("")

    context_lines.extend([
        "---",
        "",
        f"*Full hierarchy: [memory/INDEX.md](memory/INDEX.md)*",
        "",
    ])

    loaded["summary"] = "\n".join(context_lines)

    return loaded


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Session startup memory context loader.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/memory_session_loader.py
  python3 scripts/memory_session_loader.py --date 2026-03-17
  python3 scripts/memory_session_loader.py --quiet
  python3 scripts/memory_session_loader.py --json
        """,
    )
    parser.add_argument("--date", help="Date to load memory for (YYYY-MM-DD). Default: today UTC.")
    parser.add_argument("--quiet", action="store_true", help="Minimal output.")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="Output as JSON (for programmatic use).")
    args = parser.parse_args()

    if not args.quiet and not args.as_json:
        print(f"🧠 Memory Session Loader")
        print(f"   Loading context for: {args.date or 'today'}\n")

    result = load_session_memory(
        date_str=args.date,
        quiet=args.quiet,
        as_json=args.as_json,
    )

    if not result:
        return

    if args.as_json:
        # Output JSON without large content fields (paths only)
        output = {
            "daily": {"path": result["daily"]["path"]} if result.get("daily") else None,
            "weekly": {"path": result["weekly"]["path"]} if result.get("weekly") else None,
            "monthly": {"path": result["monthly"]["path"]} if result.get("monthly") else None,
            "available": result.get("available", {}),
            "date": args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        print(json.dumps(output, indent=2))
        return

    if not args.quiet:
        print(result.get("summary", ""))
        print("\n✅ Memory context loaded. Daily log ready for today's entries.")
        print(f"   Use: belam log \"message\" or python3 scripts/log_memory.py \"message\"")
    else:
        # Quiet mode: just print the summary block
        print(result.get("summary", ""))


if __name__ == "__main__":
    main()
