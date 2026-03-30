#!/usr/bin/env python3
"""
memory_monthly_consolidation.py — Monthly memory roll-up.

Reads weekly summaries + lessons/decisions created that month,
produces a monthly summary. Cross-links weekly ↔ monthly.

Runs: 1st of month 04:00 UTC via cron.

Usage:
  python3 scripts/memory_monthly_consolidation.py              # Process last complete month
  python3 scripts/memory_monthly_consolidation.py --month 2026-03
  python3 scripts/memory_monthly_consolidation.py --dry-run
  python3 scripts/memory_monthly_consolidation.py --force
"""

import argparse
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
MEMORY_DIR = WORKSPACE / "memory"
WEEKLY_DIR = MEMORY_DIR / "weekly"
MONTHLY_DIR = MEMORY_DIR / "monthly"
LESSONS_DIR = WORKSPACE / "lessons"
DECISIONS_DIR = WORKSPACE / "decisions"

MONTHLY_KEEP = 12


def last_complete_month() -> str:
    today = datetime.now(timezone.utc)
    first_of_this = today.replace(day=1)
    last_month = first_of_this - timedelta(days=1)
    return last_month.strftime("%Y-%m")


def month_range(month_str: str) -> tuple[datetime, datetime]:
    year, month = month_str.split("-")
    start = datetime(int(year), int(month), 1, tzinfo=timezone.utc)
    if int(month) == 12:
        end = datetime(int(year) + 1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
    else:
        end = datetime(int(year), int(month) + 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
    return start, end


def gather_weeklies(start: datetime, end: datetime) -> list[tuple[str, str, Path]]:
    """Return [(week_str, content, path)] for weeklies overlapping the month."""
    results = []
    if not WEEKLY_DIR.exists():
        return results
    for f in sorted(WEEKLY_DIR.glob("????-W??.md")):
        # Parse week range from frontmatter
        content = f.read_text()
        period_match = re.search(r'period:\s*"([^"]+)"', content)
        if period_match:
            try:
                week_start_str = period_match.group(1).split("→")[0].strip()
                week_start = datetime.strptime(week_start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if start <= week_start <= end or (week_start < start and week_start + timedelta(days=6) >= start):
                    results.append((f.stem, content, f))
            except (ValueError, IndexError):
                pass
    # Also check archive
    archive_dir = MEMORY_DIR / "archive" / "weekly"
    if archive_dir.exists():
        for f in sorted(archive_dir.glob("????-W??.md")):
            content = f.read_text()
            period_match = re.search(r'period:\s*"([^"]+)"', content)
            if period_match:
                try:
                    week_start_str = period_match.group(1).split("→")[0].strip()
                    week_start = datetime.strptime(week_start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    if start <= week_start <= end:
                        results.append((f.stem, content, f))
                except (ValueError, IndexError):
                    pass
    return results


def _parse_primitive_date(path: Path) -> datetime | None:
    try:
        text = path.read_text()
        for line in text.split("\n")[:10]:
            m = re.match(r"^date:\s*(\d{4}-\d{2}-\d{2})", line)
            if m:
                return datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except (OSError, ValueError):
        return None


def _parse_primitive_title(path: Path) -> str:
    title = path.stem.replace("-", " ").title()
    try:
        text = path.read_text()
        for line in text.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break
            elif line.startswith("title:"):
                title = line.split(":", 1)[1].strip().strip('"')
                break
    except OSError:
        pass
    return title


def gather_primitives(start: datetime, end: datetime) -> tuple[list[tuple[str, Path]], list[tuple[str, Path]]]:
    lessons = []
    decisions = []
    end_plus = end + timedelta(days=1)
    for directory, output in [(LESSONS_DIR, lessons), (DECISIONS_DIR, decisions)]:
        if not directory.exists():
            continue
        for f in sorted(directory.glob("*.md")):
            pdate = _parse_primitive_date(f)
            if pdate and start <= pdate < end_plus:
                title = _parse_primitive_title(f)
                output.append((title, f))
    return lessons, decisions


def extract_weekly_highlights(content: str) -> list[str]:
    """Extract key highlights from a weekly summary."""
    highlights = []
    lines = content.split("\n")
    for i, line in enumerate(lines):
        # Grab bullet points under "Daily Highlights" sections
        if line.startswith("- **") and "**:" in line:
            highlights.append(line[2:])  # Strip leading "- "
        elif line.startswith("- [") and ("Lesson" in line or "Decision" in line):
            highlights.append(line[2:])
    return highlights[:10]  # Cap at 10 per weekly


def create_monthly_file(month_str: str, start: datetime, end: datetime,
                        weeklies: list[tuple[str, str, Path]],
                        lessons: list[tuple[str, Path]],
                        decisions: list[tuple[str, Path]],
                        dry_run: bool = False) -> Path:
    MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
    monthly_file = MONTHLY_DIR / f"{month_str}.md"
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        f"---",
        f"type: memory",
        f"level: monthly",
        f"period: \"{month_str}\"",
        f"generated: \"{now_ts}\"",
        f"weekly_count: {len(weeklies)}",
        f"lessons_count: {len(lessons)}",
        f"decisions_count: {len(decisions)}",
        f"---",
        f"",
        f"# Monthly Summary — {month_str}",
        f"",
        f"*Generated: {now_ts}*",
        f"",
        f"---",
        f"",
    ]

    # Weekly summaries
    if weeklies:
        lines.append("## Weekly Summaries")
        lines.append("")
        for week_str, content, path in weeklies:
            lines.append(f"### [{week_str}](../weekly/{path.name})")
            lines.append("")
            highlights = extract_weekly_highlights(content)
            if highlights:
                for h in highlights:
                    lines.append(f"- {h}")
            else:
                lines.append("- *(no highlights extracted)*")
            lines.append("")

    # All lessons for the month
    if lessons:
        lines.append(f"## 📝 Lessons ({len(lessons)})")
        lines.append("")
        for title, path in lessons:
            rel = f"../../lessons/{path.name}"
            lines.append(f"- [{title}]({rel})")
        lines.append("")

    # All decisions for the month
    if decisions:
        lines.append(f"## ⚖️ Decisions ({len(decisions)})")
        lines.append("")
        for title, path in decisions:
            rel = f"../../decisions/{path.name}"
            lines.append(f"- [{title}]({rel})")
        lines.append("")

    lines.append("---")
    lines.append(f"*{len(weeklies)} weeks, {len(lessons)} lessons, {len(decisions)} decisions*")

    content = "\n".join(lines)

    if dry_run:
        print(f"\n[DRY RUN] Would write: {monthly_file}")
        print("─" * 60)
        print(content[:3000])
        print("─" * 60)
        return monthly_file

    monthly_file.write_text(content)
    print(f"✓ Created: {monthly_file.relative_to(WORKSPACE)}")
    return monthly_file


def main():
    parser = argparse.ArgumentParser(description="Monthly memory consolidation.")
    parser.add_argument("--month", help="Month (e.g. 2026-03). Default: last complete month.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    month_str = args.month or last_complete_month()
    start, end = month_range(month_str)

    print(f"📅 Monthly Consolidation — {month_str}")

    monthly_file = MONTHLY_DIR / f"{month_str}.md"
    if monthly_file.exists() and not args.force:
        print(f"ℹ️  Already exists. Use --force to regenerate.")
        return

    weeklies = gather_weeklies(start, end)
    print(f"📋 Weeklies: {len(weeklies)}")

    lessons, decisions = gather_primitives(start, end)
    print(f"📝 Lessons: {len(lessons)}")
    print(f"⚖️  Decisions: {len(decisions)}")

    create_monthly_file(month_str, start, end, weeklies, lessons, decisions, dry_run=args.dry_run)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}✅ Done — {month_str}")


if __name__ == "__main__":
    main()
