#!/usr/bin/env python3
"""
memory_weekly_consolidation.py — Weekly memory hierarchy roll-up.

Consolidates daily memory files into a weekly summary with importance decay,
staleness detection, cross-linking, archiving, and INDEX.md updates.

Runs: Monday 03:00 UTC via cron.

Usage:
  python3 scripts/memory_weekly_consolidation.py              # Process last complete week
  python3 scripts/memory_weekly_consolidation.py --week 2026-W12
  python3 scripts/memory_weekly_consolidation.py --dry-run    # Preview only
  python3 scripts/memory_weekly_consolidation.py --force      # Re-run even if weekly exists
"""

import argparse
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
MEMORY_DIR = WORKSPACE / "memory"
WEEKLY_DIR = MEMORY_DIR / "weekly"
KNOWLEDGE_DIR = WORKSPACE / "knowledge"
TASKS_DIR = WORKSPACE / "tasks"
PIPELINES_DIR = WORKSPACE / "pipelines"

CATEGORIES = ["insight", "decision", "preference", "context", "event", "technical", "relationship"]
CATEGORY_ICONS = {
    "insight": "💡", "decision": "⚖️", "preference": "⭐", "context": "📍",
    "event": "📅", "technical": "🔧", "relationship": "🤝",
}

# Topic keywords for wiki cross-linking (subset of weekly_knowledge_sync.py)
TOPIC_KEYWORDS = {
    "snn-architecture": ["snn", "neuron", "leaky", "synaptic", "spike", "membrane", "snntorch", "lif", "spiking neural"],
    "financial-encoding": ["delta encoding", "rate coding", "population coding", "financial", "btc", "bitcoin", "candle", "ohlcv"],
    "gpu-optimization": ["gpu", "cuda", "tpu", "a100", "t4", "colab", "batch size", "mixed precision", "fp16"],
    "agent-coordination": ["agent", "subagent", "orchestrat", "coordinator", "heartbeat", "openclaw", "cron", "telegram"],
    "experiment-methodology": ["experiment", "hypothesis", "accuracy", "loss", "metric", "sharpe", "backtest", "pipeline", "notebook"],
    "ml-architecture": ["lstm", "transformer", "attention", "neural network", "gradient", "optimizer", "adam"],
    "research-workflow": ["lesson", "insight", "decision", "knowledge", "memory", "consolidat", "workflow"],
}

DAILY_KEEP = 7
WEEKLY_KEEP = 5


# ─── Date helpers ─────────────────────────────────────────────────────────────

def get_week_range(week_str: str) -> tuple[datetime, datetime]:
    """Parse '2026-W12' and return (monday, sunday) datetimes."""
    parts = week_str.split("-W")
    year, week = int(parts[0]), int(parts[1])
    monday = datetime.fromisocalendar(year, week, 1).replace(tzinfo=timezone.utc)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def week_str_for_date(d: datetime) -> str:
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def last_complete_week_str() -> str:
    """Return the ISO week string for the most recently completed week."""
    today = datetime.now(timezone.utc)
    # Last Monday = today minus today's weekday (0=Mon) minus 7
    last_monday = today - timedelta(days=today.weekday() + 7)
    return week_str_for_date(last_monday)


# ─── Parsing ──────────────────────────────────────────────────────────────────

def parse_consolidated_entries(daily_file: Path, date_str: str) -> list[dict]:
    """
    Extract entries from a daily memory file's consolidated section.
    Returns list of {category, importance, content, tags, date}.
    """
    if not daily_file.exists():
        return []

    text = daily_file.read_text()
    entries = []

    # Find the consolidated entries section
    consolidated_match = re.search(r"## Consolidated Entries[^\n]*\n", text)
    if not consolidated_match:
        # Fall back to raw entry sections: ## TIMESTAMP — category ICONS
        return _parse_raw_entry_sections(text, date_str)

    section_text = text[consolidated_match.start():]

    current_category = "context"
    for line in section_text.splitlines():
        # Category header: ### 🔧 Technical (3)
        cat_match = re.match(r"^### [^\w]*(\w+)", line)
        if cat_match:
            cat_name = cat_match.group(1).lower()
            if cat_name in CATEGORIES:
                current_category = cat_name
            continue

        # Entry line: - **[★★★★☆]** content
        entry_match = re.match(r"^- \*\*\[([★☆]+)\]\*\* (.+)", line)
        if entry_match:
            stars = entry_match.group(1)
            importance = stars.count("★")
            content = entry_match.group(2).strip()
            entries.append({
                "category": current_category,
                "importance": importance,
                "content": content,
                "tags": [],
                "date": date_str,
                "stale": False,
            })
            continue

        # Tags line following an entry: *tags: a, b, c*
        if entries and re.match(r"^\s+\*tags:", line):
            tags_match = re.search(r"\*tags: ([^*]+)\*", line)
            if tags_match:
                entries[-1]["tags"] = [t.strip() for t in tags_match.group(1).split(",") if t.strip()]

    return entries


def _parse_raw_entry_sections(text: str, date_str: str) -> list[dict]:
    """Fallback: parse raw ## TIMESTAMP — category entries."""
    entries = []
    pattern = re.compile(
        r"## (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) — (\w+) (⚡*)\n\n(.*?)(?=\n## |\n---|\Z)",
        re.DOTALL
    )
    for m in pattern.finditer(text):
        ts, category, importance_icons, body = m.groups()
        importance = len(importance_icons)
        if importance == 0:
            importance = 3
        # First non-empty line of body is the content
        content_lines = [l.strip() for l in body.strip().splitlines() if l.strip()
                         and not l.startswith("*") and not l.startswith("#")]
        if not content_lines:
            continue
        content = content_lines[0]
        entries.append({
            "category": category if category in CATEGORIES else "context",
            "importance": importance,
            "content": content,
            "tags": [],
            "date": date_str,
            "stale": False,
        })
    return entries


# ─── Staleness detection ──────────────────────────────────────────────────────

def _load_task_statuses() -> dict[str, str]:
    """Return {slug → status} for all tasks."""
    statuses = {}
    if not TASKS_DIR.exists():
        return statuses
    for f in TASKS_DIR.glob("*.md"):
        text = f.read_text()
        m = re.search(r"^status:\s*(\S+)", text, re.MULTILINE)
        if m:
            statuses[f.stem] = m.group(1).lower()
    return statuses


def _load_pipeline_statuses() -> dict[str, str]:
    """Return {slug → status} for all pipelines."""
    statuses = {}
    if not PIPELINES_DIR.exists():
        return statuses
    for f in PIPELINES_DIR.glob("*.md"):
        text = f.read_text()
        m = re.search(r"^status:\s*(\S+)", text, re.MULTILINE)
        if m:
            statuses[f.stem] = m.group(1).lower()
    return statuses


def mark_stale_entries(entries: list[dict]) -> list[dict]:
    """Mark entries as stale if they reference completed/archived tasks or pipelines."""
    task_statuses = _load_task_statuses()
    pipeline_statuses = _load_pipeline_statuses()

    for entry in entries:
        content_lower = entry["content"].lower()

        # Check task references
        for slug, status in task_statuses.items():
            if status in ("complete", "archived", "done") and slug.replace("-", " ") in content_lower:
                entry["stale"] = True
                break

        # Check pipeline references: look for "v4", "v3", etc. patterns
        if not entry["stale"]:
            for slug, status in pipeline_statuses.items():
                if status in ("archived", "complete"):
                    # Check if pipeline version slug appears in content
                    ver = re.sub(r"[^a-z0-9]", "", slug.lower())
                    if ver and ver in content_lower.replace("-", "").replace(" ", ""):
                        entry["stale"] = True
                        break

    return entries


# ─── Importance decay ─────────────────────────────────────────────────────────

def apply_weekly_decay(entries: list[dict]) -> list[dict]:
    """
    Apply importance decay for daily → weekly consolidation:
    - imp >= 4: keep full detail
    - imp == 3: one-liner summary (first 120 chars)
    - imp <= 2: drop unless only entry in category
    """
    # Group by category
    by_category: dict[str, list[dict]] = {cat: [] for cat in CATEGORIES}
    for e in entries:
        if not e.get("stale"):
            cat = e.get("category", "context")
            if cat not in by_category:
                by_category["context"] = []
                cat = "context"
            by_category[cat].append(e)

    result = []
    for cat, cat_entries in by_category.items():
        if not cat_entries:
            continue

        # Sort by importance desc
        cat_entries.sort(key=lambda e: e["importance"], reverse=True)

        kept = []
        for e in cat_entries:
            imp = e["importance"]
            if imp >= 4:
                kept.append({**e, "summary_mode": False})
            elif imp == 3:
                # One-liner: truncate content
                content = e["content"]
                if len(content) > 120:
                    content = content[:117] + "…"
                kept.append({**e, "content": content, "summary_mode": True})
            else:
                # imp <= 2: only keep if it's the sole entry in this category
                pass

        # If nothing survived and there were entries, keep the top one as one-liner
        if not kept and cat_entries:
            top = cat_entries[0]
            content = top["content"]
            if len(content) > 120:
                content = content[:117] + "…"
            kept.append({**top, "content": content, "summary_mode": True})

        result.extend(kept)

    return result


# ─── Wiki cross-linking ───────────────────────────────────────────────────────

def detect_topics(text: str) -> list[str]:
    """Detect which knowledge topics are relevant in text."""
    text_lower = text.lower()
    matched = []
    for topic_slug, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                matched.append(topic_slug)
                break
    return matched


def add_link_to_file(filepath: Path, link_text: str, anchor_section: str = None,
                     dry_run: bool = False) -> bool:
    """
    Add a link to a file if it doesn't already exist.
    Appends to end or to a specific section.
    Returns True if modified.
    """
    if not filepath.exists():
        return False

    content = filepath.read_text()

    # Check if link already exists (by checking the URL part)
    url_match = re.search(r"\(([^)]+)\)", link_text)
    if url_match:
        url = url_match.group(1)
        if url in content:
            return False  # Already linked

    if dry_run:
        print(f"  [DRY RUN] Would add to {filepath.name}: {link_text}")
        return True

    # Find or create a "See Also" or "Links" section, or append at end
    if "## See Also" in content:
        content = content.rstrip() + f"\n{link_text}\n"
    elif "## Links" in content:
        content = content.rstrip() + f"\n{link_text}\n"
    else:
        content = content.rstrip() + f"\n\n## See Also\n\n{link_text}\n"

    filepath.write_text(content)
    return True


def cross_link_weekly_to_wiki(weekly_file: Path, entries: list[dict],
                               daily_files: list[Path], dry_run: bool = False):
    """Add links between weekly file and relevant knowledge wiki pages."""
    if not KNOWLEDGE_DIR.exists():
        return

    # Collect all content for topic detection
    all_content = " ".join(e["content"] for e in entries)
    topics = detect_topics(all_content)

    added_to_weekly = []
    for topic_slug in topics:
        wiki_file = KNOWLEDGE_DIR / f"{topic_slug}.md"
        if not wiki_file.exists():
            continue

        # Add link in weekly → wiki
        rel_path = f"../../knowledge/{topic_slug}.md"
        topic_name = topic_slug.replace("-", " ").title()
        link = f"- [→ Wiki: {topic_name}]({rel_path})"
        added_to_weekly.append(link)

        # Add link in wiki → weekly
        week_str = weekly_file.stem  # e.g. "2026-W12"
        weekly_rel = f"../memory/weekly/{weekly_file.name}"
        wiki_link = f"- [→ Weekly {week_str}]({weekly_rel})"
        add_link_to_file(wiki_file, wiki_link, dry_run=dry_run)

    if added_to_weekly:
        wiki_section = "\n\n## Wiki Cross-References\n\n" + "\n".join(added_to_weekly) + "\n"
        if dry_run:
            print(f"  [DRY RUN] Would add wiki links to {weekly_file.name}:")
            print(wiki_section)
        else:
            if weekly_file.exists():
                content = weekly_file.read_text()
                if "## Wiki Cross-References" not in content:
                    weekly_file.write_text(content.rstrip() + wiki_section)


def cross_link_daily_to_weekly(daily_file: Path, weekly_file: Path,
                                week_str: str, dry_run: bool = False):
    """Add a link from a daily file pointing to the weekly summary."""
    if not daily_file.exists():
        return

    content = daily_file.read_text()
    # Check if link already exists
    if week_str in content and "weekly/" in content:
        return

    link = f"\n*[→ Weekly {week_str}](weekly/{weekly_file.name})*\n"
    if dry_run:
        print(f"  [DRY RUN] Would add weekly link to {daily_file.name}")
        return

    daily_file.write_text(content.rstrip() + link)


# ─── Weekly file creation ─────────────────────────────────────────────────────

def create_weekly_file(week_str: str, monday: datetime, sunday: datetime,
                        entries: list[dict], daily_files: list[Path],
                        dry_run: bool = False) -> Path:
    """Create or update the weekly summary file."""
    WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    weekly_file = WEEKLY_DIR / f"{week_str}.md"

    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    week_range = f"{monday.strftime('%Y-%m-%d')} → {sunday.strftime('%Y-%m-%d')}"

    # Build navigation links to daily files
    daily_links = []
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i in range(7):
        day = monday + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        df = MEMORY_DIR / f"{day_str}.md"
        if df.exists() or any(d.name == f"{day_str}.md" for d in daily_files):
            daily_links.append(f"[{day_names[i]} {day_str}](../{day_str}.md)")

    # Derive month for upward link
    month_str = monday.strftime("%Y-%m")
    quarterly = f"2026-Q{((monday.month - 1) // 3) + 1}"

    # Collect all tags from entries
    all_tags = set()
    for e in entries:
        for t in e.get("tags", []):
            all_tags.add(t)
    # Also detect topic tags from content
    all_content = " ".join(e["content"] for e in entries)
    detected = []
    for topic_slug, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in all_content.lower():
                detected.append(topic_slug)
                break
    # Merge and limit
    top_tags = sorted(all_tags)[:8] if all_tags else detected[:5]

    lines = [
        f"---",
        f"type: memory",
        f"level: weekly",
        f"period: \"{week_range}\"",
        f"title: \"Weekly Summary — {week_str}\"",
        f"generated: \"{now_ts}\"",
        f"entry_count: {len(entries)}",
        f"daily_files: {len(daily_links)}",
        f"tags: [{', '.join(top_tags)}]",
        f"---",
        f"",
        f"# Weekly Memory Summary — {week_str}",
        f"",
        f"*Week: {week_range}*  ",
        f"*Generated: {now_ts}*",
        f"",
        f"## Navigation",
        f"",
        f"- [→ Monthly {month_str}](../monthly/{month_str}.md)",
        f"- [→ Quarterly {quarterly}](../quarterly/{quarterly}.md)",
        f"- **Daily files:** " + " | ".join(daily_links) if daily_links else "- *(no daily files found)*",
        f"",
        f"---",
        f"",
    ]

    # Group by category
    by_category: dict[str, list[dict]] = {cat: [] for cat in CATEGORIES}
    for e in entries:
        cat = e.get("category", "context")
        if cat not in by_category:
            by_category["context"] = by_category.get("context", [])
            cat = "context"
        by_category[cat].append(e)

    total_entries = 0
    for cat in CATEGORIES:
        cat_entries = by_category.get(cat, [])
        if not cat_entries:
            continue

        icon = CATEGORY_ICONS.get(cat, "•")
        lines.append(f"## {icon} {cat.title()} ({len(cat_entries)})")
        lines.append("")

        for e in sorted(cat_entries, key=lambda x: x["date"]):
            imp = e["importance"]
            stars = "★" * imp + "☆" * (5 - imp)
            content = e["content"]
            date_str = e["date"]
            tags = e.get("tags", [])
            summary_mode = e.get("summary_mode", False)

            lines.append(f"<!-- chrono:{date_str} -->")
            lines.append(f"- **[{stars}]** {content}")
            if not summary_mode and tags:
                lines.append(f"  *tags: {', '.join(tags)}*")
            lines.append(f"  *from: {date_str}*")
            total_entries += 1

        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"*{total_entries} entries consolidated from {len(daily_links)} daily files*")
    lines.append("")

    content = "\n".join(lines)

    if dry_run:
        print(f"\n[DRY RUN] Would write: {weekly_file}")
        print("─" * 60)
        print(content[:2000])
        if len(content) > 2000:
            print(f"... [{len(content) - 2000} more chars]")
        print("─" * 60)
        return weekly_file

    weekly_file.write_text(content)
    print(f"✓ Created weekly summary: {weekly_file.relative_to(WORKSPACE)}")
    return weekly_file


# ─── Archiving ────────────────────────────────────────────────────────────────

def archive_old_dailies(dry_run: bool = False) -> int:
    """Keep DAILY_KEEP daily files in memory/. Archive older ones."""
    daily_files = sorted(MEMORY_DIR.glob("????-??-??.md"))
    if len(daily_files) <= DAILY_KEEP:
        return 0

    to_archive = daily_files[:-DAILY_KEEP]
    archived = 0
    for f in to_archive:
        try:
            file_date = datetime.strptime(f.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        yyyy_mm = file_date.strftime("%Y-%m")
        dest_dir = MEMORY_DIR / "archive" / "daily" / yyyy_mm
        if dry_run:
            print(f"  [DRY RUN] Would archive daily: {f.name} → archive/daily/{yyyy_mm}/")
        else:
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(dest_dir / f.name))
        archived += 1

    return archived


def archive_old_weeklies(dry_run: bool = False) -> int:
    """Keep WEEKLY_KEEP weekly files visible. Archive older ones."""
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
            print(f"  [DRY RUN] Would archive weekly: {f.name} → archive/weekly/")
        else:
            archive_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(archive_dir / f.name))
        archived += 1

    return archived


# ─── INDEX.md ─────────────────────────────────────────────────────────────────

def extract_key_topics(file_path: Path, max_topics: int = 5) -> list[str]:
    """Extract key topics from a memory file by looking at tags and category headers."""
    if not file_path.exists():
        return []

    text = file_path.read_text()
    topics = set()

    # Extract tags from entries
    for m in re.finditer(r"\*tags: ([^*]+)\*", text):
        for tag in m.group(1).split(","):
            tag = tag.strip()
            if tag and len(tag) > 2:
                topics.add(tag)
            if len(topics) >= max_topics:
                break

    # If not enough, try to detect from content
    if len(topics) < 3:
        all_text = " ".join(line.strip() for line in text.splitlines() if line.strip())
        for t in detect_topics(all_text):
            topics.add(t.replace("-", " "))

    return sorted(topics)[:max_topics]


def update_index(dry_run: bool = False):
    """Regenerate memory/INDEX.md with all active memory files."""
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# Memory Index",
        "",
        f"*Auto-generated: {now_ts}*",
        "",
    ]

    # Daily files
    daily_files = sorted(MEMORY_DIR.glob("????-??-??.md"))
    lines.append(f"## Active Daily ({len(daily_files)})")
    lines.append("")
    lines.append("| File | Date | Key Topics |")
    lines.append("|------|------|------------|")
    for f in daily_files:
        topics = extract_key_topics(f)
        topics_str = ", ".join(topics) if topics else "*(general)*"
        lines.append(f"| [memory/{f.name}]({f.name}) | {f.stem} | {topics_str} |")
    lines.append("")

    # Weekly files
    weekly_files = sorted(WEEKLY_DIR.glob("????-W??.md")) if WEEKLY_DIR.exists() else []
    lines.append(f"## Active Weekly ({len(weekly_files)})")
    lines.append("")
    if weekly_files:
        lines.append("| File | Week | Key Topics |")
        lines.append("|------|------|------------|")
        for f in weekly_files:
            topics = extract_key_topics(f)
            topics_str = ", ".join(topics) if topics else "*(general)*"
            lines.append(f"| [memory/weekly/{f.name}](weekly/{f.name}) | {f.stem} | {topics_str} |")
    else:
        lines.append("*(no weekly files yet)*")
    lines.append("")

    # Monthly files
    monthly_dir = MEMORY_DIR / "monthly"
    monthly_files = sorted(monthly_dir.glob("????-??.md")) if monthly_dir.exists() else []
    lines.append(f"## Active Monthly ({len(monthly_files)})")
    lines.append("")
    if monthly_files:
        lines.append("| File | Month | Key Topics |")
        lines.append("|------|-------|------------|")
        for f in monthly_files:
            topics = extract_key_topics(f)
            topics_str = ", ".join(topics) if topics else "*(general)*"
            lines.append(f"| [memory/monthly/{f.name}](monthly/{f.name}) | {f.stem} | {topics_str} |")
    else:
        lines.append("*(no monthly files yet)*")
    lines.append("")

    # Quarterly files
    quarterly_dir = MEMORY_DIR / "quarterly"
    quarterly_files = sorted(quarterly_dir.glob("????-Q?.md")) if quarterly_dir.exists() else []
    lines.append(f"## Active Quarterly ({len(quarterly_files)})")
    lines.append("")
    if quarterly_files:
        lines.append("| File | Quarter | Key Topics |")
        lines.append("|------|---------|------------|")
        for f in quarterly_files:
            topics = extract_key_topics(f)
            topics_str = ", ".join(topics) if topics else "*(general)*"
            lines.append(f"| [memory/quarterly/{f.name}](quarterly/{f.name}) | {f.stem} | {topics_str} |")
    else:
        lines.append("*(no quarterly files yet)*")
    lines.append("")

    # Yearly files
    yearly_dir = MEMORY_DIR / "yearly"
    yearly_files = sorted(yearly_dir.glob("????.md")) if yearly_dir.exists() else []
    lines.append(f"## Yearly ({len(yearly_files)})")
    lines.append("")
    if yearly_files:
        for f in yearly_files:
            lines.append(f"- [memory/yearly/{f.name}](yearly/{f.name}) — {f.stem}")
    else:
        lines.append("*(no yearly files yet)*")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Navigate: [Daily](.) → [Weekly](weekly/) → [Monthly](monthly/) → [Quarterly](quarterly/) → [Yearly](yearly/)*")
    lines.append("")

    content = "\n".join(lines)
    index_file = MEMORY_DIR / "INDEX.md"

    if dry_run:
        print(f"\n[DRY RUN] Would write: {index_file.relative_to(WORKSPACE)}")
        print(content[:1000])
        return

    index_file.write_text(content)
    print(f"✓ Updated {index_file.relative_to(WORKSPACE)}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Weekly memory hierarchy roll-up.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/memory_weekly_consolidation.py
  python3 scripts/memory_weekly_consolidation.py --week 2026-W12
  python3 scripts/memory_weekly_consolidation.py --dry-run
  python3 scripts/memory_weekly_consolidation.py --force
        """,
    )
    parser.add_argument("--week", help="ISO week to process (e.g. 2026-W12). Default: last complete week.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes")
    parser.add_argument("--force", action="store_true", help="Re-run even if weekly file already exists")
    args = parser.parse_args()

    week_str = args.week or last_complete_week_str()
    monday, sunday = get_week_range(week_str)

    print(f"📅 Weekly Memory Consolidation — {week_str}")
    print(f"   Range: {monday.strftime('%Y-%m-%d')} → {sunday.strftime('%Y-%m-%d')}")
    if args.dry_run:
        print("   Mode: DRY RUN\n")

    weekly_file = WEEKLY_DIR / f"{week_str}.md"
    if weekly_file.exists() and not args.force:
        print(f"ℹ️  Weekly file already exists: {weekly_file.relative_to(WORKSPACE)}")
        print("   Use --force to regenerate.")
    else:
        # ── Step 1: Collect entries from daily files ──────────────────────────
        print(f"\n📋 Step 1: Collecting entries from daily files ({week_str})")
        all_entries = []
        daily_files_found = []

        for i in range(7):
            day = monday + timedelta(days=i)
            date_str = day.strftime("%Y-%m-%d")
            daily_file = MEMORY_DIR / f"{date_str}.md"

            # Also check archive
            if not daily_file.exists():
                yyyy_mm = day.strftime("%Y-%m")
                archived = MEMORY_DIR / "archive" / "daily" / yyyy_mm / f"{date_str}.md"
                if archived.exists():
                    daily_file = archived

            if daily_file.exists():
                entries = parse_consolidated_entries(daily_file, date_str)
                print(f"  {date_str}: {len(entries)} entries")
                all_entries.extend(entries)
                daily_files_found.append(daily_file)
            else:
                print(f"  {date_str}: (no file)")

        print(f"  Total: {len(all_entries)} entries from {len(daily_files_found)} daily files")

        # ── Step 2: Staleness detection ───────────────────────────────────────
        print(f"\n🔍 Step 2: Staleness detection")
        all_entries = mark_stale_entries(all_entries)
        stale_count = sum(1 for e in all_entries if e.get("stale"))
        print(f"  {stale_count} entries marked as stale (will not carry forward)")

        # ── Step 3: Importance decay ──────────────────────────────────────────
        print(f"\n⚖️  Step 3: Applying importance decay")
        before = len([e for e in all_entries if not e.get("stale")])
        decayed_entries = apply_weekly_decay(all_entries)
        after = len(decayed_entries)
        print(f"  {before} active → {after} after decay")

        # ── Step 4: Create weekly file ────────────────────────────────────────
        print(f"\n📝 Step 4: Creating weekly file")
        weekly_file = create_weekly_file(
            week_str, monday, sunday, decayed_entries, daily_files_found, dry_run=args.dry_run
        )

        # ── Step 5: Cross-link daily ↔ weekly ────────────────────────────────
        print(f"\n🔗 Step 5: Cross-linking daily ↔ weekly")
        for df in daily_files_found:
            # Only link files still in the main memory/ dir (not archived)
            if df.parent == MEMORY_DIR:
                cross_link_daily_to_weekly(df, weekly_file, week_str, dry_run=args.dry_run)
                if not args.dry_run:
                    print(f"  ✓ Linked {df.name} → {weekly_file.name}")

        # ── Step 6: Cross-link weekly ↔ wiki ─────────────────────────────────
        print(f"\n🌐 Step 6: Cross-linking weekly ↔ wiki")
        cross_link_weekly_to_wiki(weekly_file, decayed_entries, daily_files_found, dry_run=args.dry_run)

    # ── Step 7: Archive old dailies ───────────────────────────────────────────
    print(f"\n📦 Step 7: Archiving old daily files (keep {DAILY_KEEP})")
    n_daily = archive_old_dailies(dry_run=args.dry_run)
    print(f"  Archived {n_daily} daily files")

    # ── Step 8: Archive old weeklies ─────────────────────────────────────────
    print(f"\n📦 Step 8: Archiving old weekly files (keep {WEEKLY_KEEP})")
    n_weekly = archive_old_weeklies(dry_run=args.dry_run)
    print(f"  Archived {n_weekly} weekly files")

    # ── Step 9: Update INDEX.md ───────────────────────────────────────────────
    print(f"\n📇 Step 9: Updating INDEX.md")
    update_index(dry_run=args.dry_run)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}✅ Weekly consolidation complete — {week_str}")

    # Trigger index re-embed (hierarchy changed)
    if not args.dry_run:
        try:
            from trigger_embed import trigger
            trigger(background=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
