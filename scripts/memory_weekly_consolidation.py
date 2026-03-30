#!/usr/bin/env python3
"""
memory_weekly_consolidation.py — Weekly memory hierarchy roll-up.

Reads freeform daily memory files + lessons/decisions created that week,
produces a concise weekly summary. Cross-links daily ↔ weekly ↔ wiki.

Runs: Monday 03:00 UTC via cron.

Usage:
  python3 scripts/memory_weekly_consolidation.py              # Process last complete week
  python3 scripts/memory_weekly_consolidation.py --week 2026-W13
  python3 scripts/memory_weekly_consolidation.py --dry-run
  python3 scripts/memory_weekly_consolidation.py --force
"""

import argparse
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
MEMORY_DIR = WORKSPACE / "memory"
WEEKLY_DIR = MEMORY_DIR / "weekly"
LESSONS_DIR = WORKSPACE / "lessons"
DECISIONS_DIR = WORKSPACE / "decisions"
KNOWLEDGE_DIR = WORKSPACE / "knowledge"

DAILY_KEEP = 14
WEEKLY_KEEP = 8

TOPIC_KEYWORDS = {
    "snn-architecture": ["snn", "neuron", "leaky", "synaptic", "spike", "membrane", "snntorch", "lif", "spiking neural"],
    "financial-encoding": ["delta encoding", "rate coding", "population coding", "btc", "bitcoin", "candle", "ohlcv", "backtest", "trading"],
    "agent-coordination": ["agent", "subagent", "orchestrat", "coordinator", "heartbeat", "openclaw", "pipeline", "multi-agent"],
    "ml-architecture": ["lstm", "transformer", "attention", "neural network", "lightgbm", "lgbm", "model", "training"],
    "quant-trading": ["hyperliquid", "leverage", "position sizing", "stop-loss", "atr", "regime", "confidence", "bridge", "live trading"],
    "infrastructure": ["cron", "systemd", "daemon", "git", "deploy", "memory", "consolidat", "render"],
}


# ─── Date helpers ─────────────────────────────────────────────────────────────

def get_week_range(week_str: str) -> tuple[datetime, datetime]:
    parts = week_str.split("-W")
    year, week = int(parts[0]), int(parts[1])
    monday = datetime.fromisocalendar(year, week, 1).replace(tzinfo=timezone.utc)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def last_complete_week_str() -> str:
    today = datetime.now(timezone.utc)
    last_monday = today - timedelta(days=today.weekday() + 7)
    iso = last_monday.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def detect_topics(text: str) -> list[str]:
    text_lower = text.lower()
    matched = []
    for slug, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                matched.append(slug)
                break
    return matched


# ─── Gather content ───────────────────────────────────────────────────────────

def gather_dailies(monday: datetime) -> list[tuple[str, str, Path]]:
    """Return [(date_str, content, path)] for each daily in the week."""
    results = []
    for i in range(7):
        day = monday + timedelta(days=i)
        date_str = day.strftime("%Y-%m-%d")
        daily_file = MEMORY_DIR / f"{date_str}.md"
        if not daily_file.exists():
            # Check archive
            archived = MEMORY_DIR / "archive" / "daily" / day.strftime("%Y-%m") / f"{date_str}.md"
            if archived.exists():
                daily_file = archived
        if daily_file.exists():
            content = daily_file.read_text()
            results.append((date_str, content, daily_file))
    return results


def extract_sections(content: str) -> list[str]:
    """Extract ## section headers and their first paragraph as highlights."""
    highlights = []
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## ") and not line.startswith("## See Also"):
            header = line[3:].strip()
            # Grab the next non-empty lines as summary (up to 3 lines)
            summary_lines = []
            j = i + 1
            while j < len(lines) and len(summary_lines) < 3:
                l = lines[j].strip()
                if l.startswith("## ") or l.startswith("---"):
                    break
                if l and not l.startswith("Created:") and not l.startswith("*[→"):
                    summary_lines.append(l)
                j += 1
            summary = " ".join(summary_lines)[:200]
            if summary:
                highlights.append(f"**{header}**: {summary}")
            else:
                highlights.append(f"**{header}**")
        i += 1
    return highlights


def _parse_primitive_date(path: Path) -> datetime | None:
    """Extract date from frontmatter `date:` field, fall back to mtime."""
    try:
        text = path.read_text()
        for line in text.split("\n")[:10]:
            m = re.match(r"^date:\s*(\d{4}-\d{2}-\d{2})", line)
            if m:
                return datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        # Fall back to mtime
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except (OSError, ValueError):
        return None


def _parse_primitive_title(path: Path) -> str:
    """Extract title from frontmatter or first heading."""
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


def gather_primitives(monday: datetime, sunday: datetime) -> tuple[list[tuple[str, Path]], list[tuple[str, Path]]]:
    """Return (lessons, decisions) created during the week as [(title, path)]."""
    lessons = []
    decisions = []
    end = sunday + timedelta(days=1)

    for directory, output in [(LESSONS_DIR, lessons), (DECISIONS_DIR, decisions)]:
        if not directory.exists():
            continue
        for f in sorted(directory.glob("*.md")):
            pdate = _parse_primitive_date(f)
            if pdate and monday <= pdate < end:
                title = _parse_primitive_title(f)
                output.append((title, f))

    return lessons, decisions


# ─── Weekly file creation ─────────────────────────────────────────────────────

def create_weekly_file(week_str: str, monday: datetime, sunday: datetime,
                       dailies: list[tuple[str, str, Path]],
                       lessons: list[tuple[str, Path]],
                       decisions: list[tuple[str, Path]],
                       dry_run: bool = False) -> Path:
    WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    weekly_file = WEEKLY_DIR / f"{week_str}.md"
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    week_range = f"{monday.strftime('%Y-%m-%d')} → {sunday.strftime('%Y-%m-%d')}"

    # Detect topics from all content
    all_text = " ".join(content for _, content, _ in dailies)
    topics = detect_topics(all_text)

    # Build daily navigation
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    daily_links = []
    for i in range(7):
        day = monday + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        if any(d == day_str for d, _, _ in dailies):
            daily_links.append(f"[{day_names[i]} {day_str}](../{day_str}.md)")

    month_str = monday.strftime("%Y-%m")

    lines = [
        f"---",
        f"type: memory",
        f"level: weekly",
        f"period: \"{week_range}\"",
        f"title: \"Weekly Summary — {week_str}\"",
        f"generated: \"{now_ts}\"",
        f"daily_count: {len(dailies)}",
        f"lessons_count: {len(lessons)}",
        f"decisions_count: {len(decisions)}",
        f"tags: [{', '.join(topics)}]",
        f"---",
        f"",
        f"# Weekly Summary — {week_str}",
        f"",
        f"*{week_range}*  ",
        f"*Generated: {now_ts}*",
        f"",
        f"**Navigation:** [← Monthly {month_str}](../monthly/{month_str}.md) | " +
        " | ".join(daily_links) if daily_links else "*(no daily files)*",
        f"",
        f"---",
        f"",
    ]

    # Daily highlights
    if dailies:
        lines.append("## Daily Highlights")
        lines.append("")
        for date_str, content, path in dailies:
            sections = extract_sections(content)
            lines.append(f"### {date_str}")
            lines.append("")
            if sections:
                for s in sections[:6]:  # Max 6 highlights per day
                    lines.append(f"- {s}")
            else:
                # Fall back to first 200 chars
                preview = content.strip()[:200].replace("\n", " ")
                lines.append(f"- {preview}...")
            lines.append("")

    # Lessons
    if lessons:
        lines.append("## 📝 Lessons Created")
        lines.append("")
        for title, path in lessons:
            rel = f"../../lessons/{path.name}"
            lines.append(f"- [{title}]({rel})")
        lines.append("")

    # Decisions
    if decisions:
        lines.append("## ⚖️ Decisions Made")
        lines.append("")
        for title, path in decisions:
            rel = f"../../decisions/{path.name}"
            lines.append(f"- [{title}]({rel})")
        lines.append("")

    # Topics detected
    if topics:
        lines.append("## Topics")
        lines.append("")
        for t in topics:
            wiki_file = KNOWLEDGE_DIR / f"{t}.md"
            if wiki_file.exists():
                lines.append(f"- [{t.replace('-', ' ').title()}](../../knowledge/{t}.md)")
            else:
                lines.append(f"- {t.replace('-', ' ').title()}")
        lines.append("")

    lines.append("---")
    lines.append(f"*{len(dailies)} daily files, {len(lessons)} lessons, {len(decisions)} decisions*")

    content = "\n".join(lines)

    if dry_run:
        print(f"\n[DRY RUN] Would write: {weekly_file}")
        print("─" * 60)
        print(content[:3000])
        if len(content) > 3000:
            print(f"... [{len(content) - 3000} more chars]")
        print("─" * 60)
        return weekly_file

    weekly_file.write_text(content)
    print(f"✓ Created: {weekly_file.relative_to(WORKSPACE)}")
    return weekly_file


# ─── Cross-linking ────────────────────────────────────────────────────────────

def cross_link_daily_to_weekly(daily_file: Path, week_str: str, dry_run: bool = False):
    if not daily_file.exists():
        return
    content = daily_file.read_text()
    link_url = f"weekly/{week_str}.md"
    if link_url in content:
        return
    link = f"\n*[→ Weekly {week_str}](weekly/{week_str}.md)*\n"
    if dry_run:
        print(f"  [DRY RUN] Would link {daily_file.name} → {week_str}")
        return
    daily_file.write_text(content.rstrip() + link)
    print(f"  ✓ Linked {daily_file.name} → {week_str}")


# ─── Archiving ────────────────────────────────────────────────────────────────

def archive_old_dailies(dry_run: bool = False) -> int:
    daily_files = sorted(MEMORY_DIR.glob("????-??-??.md"))
    if len(daily_files) <= DAILY_KEEP:
        return 0
    to_archive = daily_files[:-DAILY_KEEP]
    archived = 0
    for f in to_archive:
        try:
            file_date = datetime.strptime(f.stem, "%Y-%m-%d")
        except ValueError:
            continue
        dest_dir = MEMORY_DIR / "archive" / "daily" / file_date.strftime("%Y-%m")
        if dry_run:
            print(f"  [DRY RUN] Would archive: {f.name}")
        else:
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(dest_dir / f.name))
        archived += 1
    return archived


def archive_old_weeklies(dry_run: bool = False) -> int:
    if not WEEKLY_DIR.exists():
        return 0
    weekly_files = sorted(WEEKLY_DIR.glob("????-W??.md"))
    if len(weekly_files) <= WEEKLY_KEEP:
        return 0
    to_archive = weekly_files[:-WEEKLY_KEEP]
    archived = 0
    archive_dir = MEMORY_DIR / "archive" / "weekly"
    for f in to_archive:
        if dry_run:
            print(f"  [DRY RUN] Would archive: {f.name}")
        else:
            archive_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(archive_dir / f.name))
        archived += 1
    return archived


# ─── INDEX.md ─────────────────────────────────────────────────────────────────

def update_index(dry_run: bool = False):
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Memory Index",
        f"*Auto-generated: {now_ts}*",
        "",
    ]

    # Daily
    daily_files = sorted(MEMORY_DIR.glob("????-??-??.md"))
    lines.append(f"## Daily ({len(daily_files)})")
    for f in daily_files[-7:]:  # Show last 7
        lines.append(f"- [{f.stem}]({f.name})")
    lines.append("")

    # Weekly
    weekly_files = sorted(WEEKLY_DIR.glob("????-W??.md")) if WEEKLY_DIR.exists() else []
    lines.append(f"## Weekly ({len(weekly_files)})")
    for f in weekly_files:
        lines.append(f"- [{f.stem}](weekly/{f.name})")
    lines.append("")

    # Monthly
    monthly_dir = MEMORY_DIR / "monthly"
    monthly_files = sorted(monthly_dir.glob("????-??.md")) if monthly_dir.exists() else []
    lines.append(f"## Monthly ({len(monthly_files)})")
    for f in monthly_files:
        lines.append(f"- [{f.stem}](monthly/{f.name})")
    lines.append("")

    content = "\n".join(lines)
    index_file = MEMORY_DIR / "INDEX.md"
    if dry_run:
        print(f"\n[DRY RUN] Would update INDEX.md")
        return
    index_file.write_text(content)
    print(f"✓ Updated INDEX.md")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Weekly memory consolidation.")
    parser.add_argument("--week", help="ISO week (e.g. 2026-W13). Default: last complete week.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    week_str = args.week or last_complete_week_str()
    monday, sunday = get_week_range(week_str)

    print(f"📅 Weekly Consolidation — {week_str}")
    print(f"   {monday.strftime('%Y-%m-%d')} → {sunday.strftime('%Y-%m-%d')}")

    weekly_file = WEEKLY_DIR / f"{week_str}.md"
    if weekly_file.exists() and not args.force:
        print(f"ℹ️  Already exists. Use --force to regenerate.")
        return

    # 1. Gather dailies
    dailies = gather_dailies(monday)
    print(f"\n📋 Dailies: {len(dailies)} files found")
    for d, _, _ in dailies:
        print(f"  {d}")

    # 2. Gather lessons/decisions
    lessons, decisions = gather_primitives(monday, sunday)
    print(f"📝 Lessons: {len(lessons)}")
    for title, _ in lessons:
        print(f"  - {title}")
    print(f"⚖️  Decisions: {len(decisions)}")
    for title, _ in decisions:
        print(f"  - {title}")

    # 3. Create weekly file
    print(f"\n📝 Creating weekly summary...")
    weekly_file = create_weekly_file(
        week_str, monday, sunday, dailies, lessons, decisions, dry_run=args.dry_run,
    )

    # 4. Cross-link dailies → weekly
    print(f"\n🔗 Cross-linking")
    for _, _, path in dailies:
        if path.parent == MEMORY_DIR:
            cross_link_daily_to_weekly(path, week_str, dry_run=args.dry_run)

    # 5. Archive
    print(f"\n📦 Archiving (keep {DAILY_KEEP} daily, {WEEKLY_KEEP} weekly)")
    n_d = archive_old_dailies(dry_run=args.dry_run)
    n_w = archive_old_weeklies(dry_run=args.dry_run)
    print(f"  Archived {n_d} daily, {n_w} weekly files")

    # 6. Update INDEX
    update_index(dry_run=args.dry_run)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}✅ Done — {week_str}")


if __name__ == "__main__":
    main()
