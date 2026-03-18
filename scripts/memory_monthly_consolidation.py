#!/usr/bin/env python3
"""
memory_monthly_consolidation.py — Monthly/quarterly/yearly memory roll-up.

Consolidates weekly → monthly → quarterly → yearly with aggressive importance
decay, staleness detection, and full cross-linking between all levels.

Runs: 1st of month 04:00 UTC via cron.

Usage:
  python3 scripts/memory_monthly_consolidation.py              # Process last complete month
  python3 scripts/memory_monthly_consolidation.py --month 2026-03
  python3 scripts/memory_monthly_consolidation.py --dry-run    # Preview only
  python3 scripts/memory_monthly_consolidation.py --force      # Re-run even if exists
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
MONTHLY_DIR = MEMORY_DIR / "monthly"
QUARTERLY_DIR = MEMORY_DIR / "quarterly"
YEARLY_DIR = MEMORY_DIR / "yearly"
KNOWLEDGE_DIR = WORKSPACE / "knowledge"

CATEGORIES = ["insight", "decision", "preference", "context", "event", "technical", "relationship"]
CATEGORY_ICONS = {
    "insight": "💡", "decision": "⚖️", "preference": "⭐", "context": "📍",
    "event": "📅", "technical": "🔧", "relationship": "🤝",
}

QUARTERLY_KEEP = 5
WEEKLY_KEEP = 5

TOPIC_KEYWORDS = {
    "snn-architecture": ["snn", "neuron", "spike", "membrane", "snntorch", "lif"],
    "financial-encoding": ["financial", "btc", "bitcoin", "candle", "ohlcv", "trading"],
    "gpu-optimization": ["gpu", "cuda", "t4", "colab", "batch size", "fp16"],
    "agent-coordination": ["agent", "subagent", "orchestrat", "heartbeat", "openclaw", "cron"],
    "experiment-methodology": ["experiment", "accuracy", "loss", "sharpe", "backtest", "pipeline"],
    "ml-architecture": ["lstm", "transformer", "gradient", "optimizer", "neural network"],
    "research-workflow": ["lesson", "knowledge", "memory", "consolidat", "workflow"],
}


# ─── Date helpers ─────────────────────────────────────────────────────────────

def last_complete_month_str() -> str:
    today = datetime.now(timezone.utc)
    first_of_month = today.replace(day=1)
    last_month = first_of_month - timedelta(days=1)
    return last_month.strftime("%Y-%m")


def month_range(month_str: str) -> tuple[datetime, datetime]:
    """Return (first_day, last_day) for a month string like '2026-03'."""
    year, month = int(month_str[:4]), int(month_str[5:7])
    first = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        last = datetime(year + 1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
    else:
        last = datetime(year, month + 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
    return first, last


def quarter_for_month(month_str: str) -> str:
    """Return quarter string for a month, e.g. '2026-03' → '2026-Q1'."""
    year, month = int(month_str[:4]), int(month_str[5:7])
    q = (month - 1) // 3 + 1
    return f"{year}-Q{q}"


def months_in_quarter(quarter_str: str) -> list[str]:
    """Return list of month strings for a quarter."""
    year, q = int(quarter_str[:4]), int(quarter_str[-1])
    start_month = (q - 1) * 3 + 1
    return [f"{year}-{start_month + i:02d}" for i in range(3)]


def is_quarter_end_month(month_str: str) -> bool:
    """True if this month is the last month of a quarter (Mar, Jun, Sep, Dec)."""
    month = int(month_str[5:7])
    return month in (3, 6, 9, 12)


def quarters_in_year(year: int) -> list[str]:
    return [f"{year}-Q{q}" for q in range(1, 5)]


def week_strs_in_month(month_str: str) -> list[str]:
    """Return all ISO week strings that overlap with a given month."""
    first, last = month_range(month_str)
    weeks = set()
    current = first
    while current <= last:
        iso = current.isocalendar()
        weeks.add(f"{iso[0]}-W{iso[1]:02d}")
        current += timedelta(days=7)
    # Also check last day
    iso = last.isocalendar()
    weeks.add(f"{iso[0]}-W{iso[1]:02d}")
    return sorted(weeks)


# ─── Parsing ──────────────────────────────────────────────────────────────────

def parse_weekly_entries(weekly_file: Path) -> list[dict]:
    """Extract entries from a weekly summary file."""
    if not weekly_file.exists():
        return []

    text = weekly_file.read_text()
    entries = []

    # Extract week string from filename
    week_str = weekly_file.stem  # e.g. "2026-W12"

    current_category = "context"
    current_date = week_str  # fallback date

    for line in text.splitlines():
        # Category header
        cat_match = re.match(r"^## [^\w]*(\w+)", line)
        if cat_match:
            cat_name = cat_match.group(1).lower()
            if cat_name in CATEGORIES:
                current_category = cat_name
            continue

        # Chrono tag
        chrono_match = re.match(r"<!-- chrono:(\d{4}-\d{2}-\d{2}) -->", line)
        if chrono_match:
            current_date = chrono_match.group(1)
            continue

        # Entry line
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
                "date": current_date,
                "week": week_str,
                "stale": False,
                "summary_mode": False,
            })
            continue

        # Tags line
        if entries and re.match(r"^\s+\*tags:", line):
            tags_match = re.search(r"\*tags: ([^*]+)\*", line)
            if tags_match:
                entries[-1]["tags"] = [t.strip() for t in tags_match.group(1).split(",") if t.strip()]

    return entries


def parse_monthly_entries(monthly_file: Path) -> list[dict]:
    """Extract entries from a monthly summary file."""
    return _parse_summary_file(monthly_file, level="month")


def parse_quarterly_entries(quarterly_file: Path) -> list[dict]:
    """Extract entries from a quarterly summary file."""
    return _parse_summary_file(quarterly_file, level="quarter")


def _parse_summary_file(filepath: Path, level: str) -> list[dict]:
    """Generic parser for weekly/monthly/quarterly files."""
    if not filepath.exists():
        return []

    text = filepath.read_text()
    entries = []
    current_category = "context"
    current_date = filepath.stem

    for line in text.splitlines():
        cat_match = re.match(r"^## [^\w]*(\w+)", line)
        if cat_match:
            cat_name = cat_match.group(1).lower()
            if cat_name in CATEGORIES:
                current_category = cat_name
            continue

        chrono_match = re.match(r"<!-- chrono:(\d{4}-\d{2}-\d{2}) -->", line)
        if chrono_match:
            current_date = chrono_match.group(1)
            continue

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
                "date": current_date,
                "stale": False,
                "summary_mode": False,
            })
            continue

        if entries and re.match(r"^\s+\*tags:", line):
            tags_match = re.search(r"\*tags: ([^*]+)\*", line)
            if tags_match:
                entries[-1]["tags"] = [t.strip() for t in tags_match.group(1).split(",") if t.strip()]

    return entries


# ─── Importance decay ─────────────────────────────────────────────────────────

def apply_monthly_decay(entries: list[dict]) -> list[dict]:
    """
    Daily → Monthly decay (more aggressive):
    - imp >= 4: keep full detail
    - imp <= 3: one-liner or dropped
    """
    by_category: dict[str, list[dict]] = {cat: [] for cat in CATEGORIES}
    for e in entries:
        if e.get("stale"):
            continue
        cat = e.get("category", "context")
        if cat not in by_category:
            by_category["context"] = by_category.get("context", [])
            cat = "context"
        by_category[cat].append(e)

    result = []
    for cat, cat_entries in by_category.items():
        if not cat_entries:
            continue
        cat_entries.sort(key=lambda e: e["importance"], reverse=True)

        kept = []
        for e in cat_entries:
            imp = e["importance"]
            if imp >= 4:
                kept.append({**e, "summary_mode": False})
            elif imp == 3:
                content = e["content"][:100] + ("…" if len(e["content"]) > 100 else "")
                kept.append({**e, "content": content, "summary_mode": True})
            # imp <= 2: dropped unless only entry

        if not kept and cat_entries:
            top = cat_entries[0]
            content = top["content"][:100] + ("…" if len(top["content"]) > 100 else "")
            kept.append({**top, "content": content, "summary_mode": True})

        result.extend(kept)

    return result


def apply_quarterly_decay(entries: list[dict]) -> list[dict]:
    """
    Monthly → Quarterly decay (very aggressive):
    - imp == 5: keep full detail
    - imp <= 4: one-liner
    """
    by_category: dict[str, list[dict]] = {cat: [] for cat in CATEGORIES}
    for e in entries:
        if e.get("stale"):
            continue
        cat = e.get("category", "context")
        if cat not in by_category:
            by_category["context"] = by_category.get("context", [])
            cat = "context"
        by_category[cat].append(e)

    result = []
    for cat, cat_entries in by_category.items():
        if not cat_entries:
            continue
        cat_entries.sort(key=lambda e: e["importance"], reverse=True)

        # Deduplicate by content similarity
        seen_contents = []
        deduped = []
        for e in cat_entries:
            normalized = e["content"].lower()[:60]
            if not any(normalized in seen[:60] or seen[:60] in normalized for seen in seen_contents):
                deduped.append(e)
                seen_contents.append(e["content"].lower())

        kept = []
        for e in deduped:
            imp = e["importance"]
            if imp == 5:
                kept.append({**e, "summary_mode": False})
            else:
                content = e["content"][:80] + ("…" if len(e["content"]) > 80 else "")
                kept.append({**e, "content": content, "summary_mode": True})

        if not kept and cat_entries:
            top = cat_entries[0]
            content = top["content"][:80] + ("…" if len(top["content"]) > 80 else "")
            kept.append({**top, "content": content, "summary_mode": True})

        result.extend(kept)

    return result


def apply_yearly_decay(entries: list[dict]) -> list[dict]:
    """
    Quarterly → Yearly: everything is a one-liner, deduplicated heavily.
    """
    by_category: dict[str, list[dict]] = {cat: [] for cat in CATEGORIES}
    for e in entries:
        if e.get("stale"):
            continue
        cat = e.get("category", "context")
        if cat not in by_category:
            by_category["context"] = by_category.get("context", [])
            cat = "context"
        by_category[cat].append(e)

    result = []
    for cat, cat_entries in by_category.items():
        if not cat_entries:
            continue
        cat_entries.sort(key=lambda e: e["importance"], reverse=True)

        # Keep only top 3 per category, all as one-liners
        for e in cat_entries[:3]:
            content = e["content"][:70] + ("…" if len(e["content"]) > 70 else "")
            result.append({**e, "content": content, "summary_mode": True})

    return result


# ─── File creation ────────────────────────────────────────────────────────────

def _detect_level_from_title(title: str) -> str:
    """Detect memory level from title string."""
    title_lower = title.lower()
    if "yearly" in title_lower:
        return "yearly"
    elif "quarterly" in title_lower:
        return "quarterly"
    elif "monthly" in title_lower:
        return "monthly"
    return "weekly"


def _build_summary_content(title: str, level_str: str, entries: list[dict],
                             source_files: list[Path], nav_links: list[str],
                             upward_links: list[str]) -> str:
    """Build the markdown content for any summary level."""
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    level = _detect_level_from_title(title)

    # Collect tags from entries
    all_tags = set()
    for e in entries:
        for t in e.get("tags", []):
            all_tags.add(t)
    if not all_tags:
        all_content = " ".join(e.get("content", "") for e in entries)
        for topic_slug, keywords in TOPIC_KEYWORDS.items():
            for kw in keywords:
                if kw in all_content.lower():
                    all_tags.add(topic_slug)
                    break
    top_tags = sorted(all_tags)[:8]

    lines = [
        f"---",
        f"type: memory",
        f"level: {level}",
        f"period: \"{level_str}\"",
        f"title: \"{title}\"",
        f"generated: \"{now_ts}\"",
        f"entry_count: {len(entries)}",
        f"source_files: {len(source_files)}",
        f"tags: [{', '.join(top_tags)}]",
        f"---",
        f"",
        f"# {title}",
        f"",
        f"*Generated: {now_ts}*",
        f"",
        f"## Navigation",
        f"",
    ]

    for link in upward_links:
        lines.append(f"- {link}")
    if nav_links:
        lines.append(f"- **Sources:** " + " | ".join(nav_links))
    lines.append("")
    lines.append("---")
    lines.append("")

    # Group by category
    by_category: dict[str, list[dict]] = {cat: [] for cat in CATEGORIES}
    for e in entries:
        cat = e.get("category", "context")
        if cat not in by_category:
            by_category["context"] = by_category.get("context", [])
            cat = "context"
        by_category[cat].append(e)

    total = 0
    for cat in CATEGORIES:
        cat_entries = by_category.get(cat, [])
        if not cat_entries:
            continue

        icon = CATEGORY_ICONS.get(cat, "•")
        lines.append(f"## {icon} {cat.title()} ({len(cat_entries)})")
        lines.append("")

        for e in sorted(cat_entries, key=lambda x: x.get("date", "")):
            imp = e["importance"]
            stars = "★" * imp + "☆" * (5 - imp)
            content = e["content"]
            date_str = e.get("date", "")
            tags = e.get("tags", [])

            lines.append(f"<!-- chrono:{date_str} -->")
            lines.append(f"- **[{stars}]** {content}")
            if tags and not e.get("summary_mode"):
                lines.append(f"  *tags: {', '.join(tags)}*")
            if date_str:
                lines.append(f"  *from: {date_str}*")
            total += 1

        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"*{total} entries consolidated from {len(source_files)} source files*")
    lines.append("")

    return "\n".join(lines)


def create_monthly_file(month_str: str, entries: list[dict],
                         weekly_files: list[Path], dry_run: bool = False) -> Path:
    """Create or update a monthly summary file."""
    MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
    monthly_file = MONTHLY_DIR / f"{month_str}.md"

    quarter_str = quarter_for_month(month_str)
    year = month_str[:4]

    nav_links = [f"[{f.stem}](../weekly/{f.name})" for f in weekly_files]
    upward_links = [
        f"[→ Quarterly {quarter_str}](../quarterly/{quarter_str}.md)",
        f"[→ Yearly {year}](../yearly/{year}.md)",
    ]

    content = _build_summary_content(
        title=f"Monthly Memory Summary — {month_str}",
        level_str=month_str,
        entries=entries,
        source_files=weekly_files,
        nav_links=nav_links,
        upward_links=upward_links,
    )

    if dry_run:
        print(f"\n[DRY RUN] Would write: memory/monthly/{month_str}.md")
        print(content[:1500])
        if len(content) > 1500:
            print(f"... [{len(content) - 1500} more chars]")
        return monthly_file

    monthly_file.write_text(content)
    print(f"✓ Created monthly summary: {monthly_file.relative_to(WORKSPACE)}")
    return monthly_file


def create_quarterly_file(quarter_str: str, entries: list[dict],
                           monthly_files: list[Path], dry_run: bool = False) -> Path:
    """Create or update a quarterly summary file."""
    QUARTERLY_DIR.mkdir(parents=True, exist_ok=True)
    quarterly_file = QUARTERLY_DIR / f"{quarter_str}.md"

    year = quarter_str[:4]
    nav_links = [f"[{f.stem}](../monthly/{f.name})" for f in monthly_files]
    upward_links = [f"[→ Yearly {year}](../yearly/{year}.md)"]

    content = _build_summary_content(
        title=f"Quarterly Memory Summary — {quarter_str}",
        level_str=quarter_str,
        entries=entries,
        source_files=monthly_files,
        nav_links=nav_links,
        upward_links=upward_links,
    )

    if dry_run:
        print(f"\n[DRY RUN] Would write: memory/quarterly/{quarter_str}.md")
        print(content[:1000])
        return quarterly_file

    quarterly_file.write_text(content)
    print(f"✓ Created quarterly summary: {quarterly_file.relative_to(WORKSPACE)}")
    return quarterly_file


def create_yearly_file(year: str, entries: list[dict],
                        quarterly_files: list[Path], dry_run: bool = False) -> Path:
    """Create or update a yearly summary file."""
    YEARLY_DIR.mkdir(parents=True, exist_ok=True)
    yearly_file = YEARLY_DIR / f"{year}.md"

    nav_links = [f"[{f.stem}](../quarterly/{f.name})" for f in quarterly_files]
    upward_links = []

    content = _build_summary_content(
        title=f"Yearly Memory Summary — {year}",
        level_str=year,
        entries=entries,
        source_files=quarterly_files,
        nav_links=nav_links,
        upward_links=upward_links,
    )

    if dry_run:
        print(f"\n[DRY RUN] Would write: memory/yearly/{year}.md")
        print(content[:800])
        return yearly_file

    yearly_file.write_text(content)
    print(f"✓ Created yearly summary: {yearly_file.relative_to(WORKSPACE)}")
    return yearly_file


# ─── Cross-linking ────────────────────────────────────────────────────────────

def detect_topics(text: str) -> list[str]:
    text_lower = text.lower()
    matched = []
    for topic_slug, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                matched.append(topic_slug)
                break
    return matched


def add_backlink(filepath: Path, link_text: str, dry_run: bool = False) -> bool:
    """Add a link to a file's See Also section if not already present."""
    if not filepath.exists():
        return False

    content = filepath.read_text()
    url_match = re.search(r"\(([^)]+)\)", link_text)
    if url_match and url_match.group(1) in content:
        return False  # Already linked

    if dry_run:
        print(f"  [DRY RUN] Would add backlink to {filepath.name}: {link_text}")
        return True

    if "## See Also" in content:
        content = content.rstrip() + f"\n{link_text}\n"
    else:
        content = content.rstrip() + f"\n\n## See Also\n\n{link_text}\n"

    filepath.write_text(content)
    return True


def cross_link_levels(summary_file: Path, source_files: list[Path],
                       level: str, dry_run: bool = False):
    """Add backlinks from source files to summary file."""
    if not summary_file.exists() and not dry_run:
        return

    file_stem = summary_file.stem

    for src_file in source_files:
        if not src_file.exists():
            continue
        # Compute relative path from src to summary
        try:
            rel = summary_file.relative_to(src_file.parent.parent)
            rel_str = f"../{rel}"
        except ValueError:
            rel_str = str(summary_file)

        link = f"- [→ {level.title()} {file_stem}]({rel_str})"
        add_backlink(src_file, link, dry_run=dry_run)


def cross_link_to_wiki(summary_file: Path, entries: list[dict],
                        level: str, dry_run: bool = False):
    """Add cross-links between a summary file and relevant wiki pages."""
    if not KNOWLEDGE_DIR.exists():
        return

    all_content = " ".join(e["content"] for e in entries)
    topics = detect_topics(all_content)
    file_stem = summary_file.stem

    added = []
    for topic_slug in topics:
        wiki_file = KNOWLEDGE_DIR / f"{topic_slug}.md"
        if not wiki_file.exists():
            continue

        # Add link in summary → wiki
        rel_path = f"../../knowledge/{topic_slug}.md"
        topic_name = topic_slug.replace("-", " ").title()
        added.append(f"- [→ Wiki: {topic_name}]({rel_path})")

        # Add link in wiki → summary (prefer higher level)
        summary_rel = f"../memory/{level}/{summary_file.name}"
        wiki_link = f"- [→ {level.title()} {file_stem}]({summary_rel})"
        add_backlink(wiki_file, wiki_link, dry_run=dry_run)

    if added and summary_file.exists():
        wiki_section_text = "\n\n## Wiki Cross-References\n\n" + "\n".join(added) + "\n"
        if dry_run:
            print(f"  [DRY RUN] Would add {len(added)} wiki links to {summary_file.name}")
        else:
            content = summary_file.read_text()
            if "## Wiki Cross-References" not in content:
                summary_file.write_text(content.rstrip() + wiki_section_text)


# ─── Archiving ────────────────────────────────────────────────────────────────

def archive_old_quarterlies(dry_run: bool = False) -> int:
    """Keep QUARTERLY_KEEP quarterly files. Archive oldest when 6th starts."""
    if not QUARTERLY_DIR.exists():
        return 0

    quarterly_files = sorted(QUARTERLY_DIR.glob("????-Q?.md"))
    if len(quarterly_files) <= QUARTERLY_KEEP:
        return 0

    to_archive = quarterly_files[:-QUARTERLY_KEEP]
    archive_dir = MEMORY_DIR / "archive" / "quarterly"
    archived = 0

    for f in to_archive:
        if dry_run:
            print(f"  [DRY RUN] Would archive quarterly: {f.name}")
        else:
            archive_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(archive_dir / f.name))
        archived += 1

    return archived


# ─── INDEX.md (shared logic with weekly script) ───────────────────────────────

def update_index(dry_run: bool = False):
    """Regenerate memory/INDEX.md across all levels."""
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def get_topics(file_path):
        if not file_path.exists():
            return "*(general)*"
        text = file_path.read_text()
        topics = set()
        for m in re.finditer(r"\*tags: ([^*]+)\*", text):
            for tag in m.group(1).split(","):
                tag = tag.strip()
                if tag and len(tag) > 2:
                    topics.add(tag)
        return ", ".join(sorted(topics)[:5]) if topics else "*(general)*"

    lines = ["# Memory Index", "", f"*Auto-generated: {now_ts}*", ""]

    # Daily
    daily_files = sorted(MEMORY_DIR.glob("????-??-??.md"))
    lines += [f"## Active Daily ({len(daily_files)})", "",
              "| File | Date | Key Topics |", "|------|------|------------|"]
    for f in daily_files:
        lines.append(f"| [memory/{f.name}]({f.name}) | {f.stem} | {get_topics(f)} |")
    lines.append("")

    # Weekly
    weekly_files = sorted(WEEKLY_DIR.glob("????-W??.md")) if WEEKLY_DIR.exists() else []
    lines += [f"## Active Weekly ({len(weekly_files)})", ""]
    if weekly_files:
        lines += ["| File | Week | Key Topics |", "|------|------|------------|"]
        for f in weekly_files:
            lines.append(f"| [memory/weekly/{f.name}](weekly/{f.name}) | {f.stem} | {get_topics(f)} |")
    else:
        lines.append("*(no weekly files yet)*")
    lines.append("")

    # Monthly
    monthly_files = sorted(MONTHLY_DIR.glob("????-??.md")) if MONTHLY_DIR.exists() else []
    lines += [f"## Active Monthly ({len(monthly_files)})", ""]
    if monthly_files:
        lines += ["| File | Month | Key Topics |", "|------|-------|------------|"]
        for f in monthly_files:
            lines.append(f"| [memory/monthly/{f.name}](monthly/{f.name}) | {f.stem} | {get_topics(f)} |")
    else:
        lines.append("*(no monthly files yet)*")
    lines.append("")

    # Quarterly
    quarterly_files = sorted(QUARTERLY_DIR.glob("????-Q?.md")) if QUARTERLY_DIR.exists() else []
    lines += [f"## Active Quarterly ({len(quarterly_files)})", ""]
    if quarterly_files:
        lines += ["| File | Quarter | Key Topics |", "|------|---------|------------|"]
        for f in quarterly_files:
            lines.append(f"| [memory/quarterly/{f.name}](quarterly/{f.name}) | {f.stem} | {get_topics(f)} |")
    else:
        lines.append("*(no quarterly files yet)*")
    lines.append("")

    # Yearly
    yearly_files = sorted(YEARLY_DIR.glob("????.md")) if YEARLY_DIR.exists() else []
    lines += [f"## Yearly ({len(yearly_files)})", ""]
    if yearly_files:
        for f in yearly_files:
            lines.append(f"- [memory/yearly/{f.name}](yearly/{f.name}) — {f.stem}")
    else:
        lines.append("*(no yearly files yet)*")
    lines += ["", "---", "",
              "*Navigate: [Daily](.) → [Weekly](weekly/) → [Monthly](monthly/) → [Quarterly](quarterly/) → [Yearly](yearly/)*",
              ""]

    content = "\n".join(lines)
    index_file = MEMORY_DIR / "INDEX.md"

    if dry_run:
        print(f"\n[DRY RUN] Would write: {index_file.relative_to(WORKSPACE)}")
        print(content[:800])
        return

    index_file.write_text(content)
    print(f"✓ Updated {index_file.relative_to(WORKSPACE)}")


# ─── Main consolidation logic ─────────────────────────────────────────────────

def consolidate_month(month_str: str, dry_run: bool = False, force: bool = False) -> Path | None:
    """Consolidate weekly → monthly for a given month."""
    monthly_file = MONTHLY_DIR / f"{month_str}.md"
    if monthly_file.exists() and not force:
        print(f"  ℹ️  Monthly file exists: {month_str} (use --force to regen)")
        return monthly_file

    print(f"\n📅 Consolidating month: {month_str}")

    # Find weekly files for this month
    week_strs = week_strs_in_month(month_str)
    weekly_files = []
    all_entries = []

    for week_str in week_strs:
        wf = WEEKLY_DIR / f"{week_str}.md"
        if not wf.exists():
            # Check archive
            archive_wf = MEMORY_DIR / "archive" / "weekly" / f"{week_str}.md"
            if archive_wf.exists():
                wf = archive_wf

        if wf.exists():
            entries = parse_weekly_entries(wf)
            print(f"  {week_str}: {len(entries)} entries")
            all_entries.extend(entries)
            weekly_files.append(wf)

    if not all_entries:
        print(f"  No weekly entries found for {month_str}. Skipping.")
        return None

    print(f"  Total: {len(all_entries)} entries from {len(weekly_files)} weekly files")

    # Apply decay
    decayed = apply_monthly_decay(all_entries)
    print(f"  After decay: {len(decayed)} entries")

    # Create monthly file
    mf = create_monthly_file(month_str, decayed, weekly_files, dry_run=dry_run)

    # Cross-link weekly → monthly
    cross_link_levels(mf, weekly_files, "monthly", dry_run=dry_run)

    # Cross-link to wiki
    cross_link_to_wiki(mf, decayed, "monthly", dry_run=dry_run)

    return mf


def consolidate_quarter(quarter_str: str, dry_run: bool = False, force: bool = False) -> Path | None:
    """Consolidate monthly → quarterly."""
    quarterly_file = QUARTERLY_DIR / f"{quarter_str}.md"
    if quarterly_file.exists() and not force:
        print(f"  ℹ️  Quarterly file exists: {quarter_str} (use --force to regen)")
        return quarterly_file

    print(f"\n📊 Consolidating quarter: {quarter_str}")

    month_strs = months_in_quarter(quarter_str)
    monthly_files = []
    all_entries = []

    for month_str in month_strs:
        mf = MONTHLY_DIR / f"{month_str}.md"
        if mf.exists():
            entries = parse_monthly_entries(mf)
            print(f"  {month_str}: {len(entries)} entries")
            all_entries.extend(entries)
            monthly_files.append(mf)

    if not all_entries:
        print(f"  No monthly entries found for {quarter_str}. Skipping.")
        return None

    print(f"  Total: {len(all_entries)} entries from {len(monthly_files)} monthly files")

    decayed = apply_quarterly_decay(all_entries)
    print(f"  After decay: {len(decayed)} entries")

    qf = create_quarterly_file(quarter_str, decayed, monthly_files, dry_run=dry_run)

    # Cross-link monthly → quarterly
    cross_link_levels(qf, monthly_files, "quarterly", dry_run=dry_run)
    cross_link_to_wiki(qf, decayed, "quarterly", dry_run=dry_run)

    return qf


def consolidate_year(year: str, dry_run: bool = False, force: bool = False) -> Path | None:
    """Consolidate quarterly → yearly for a given year."""
    yearly_file = YEARLY_DIR / f"{year}.md"
    if yearly_file.exists() and not force:
        print(f"  ℹ️  Yearly file exists: {year} (use --force to regen)")
        return yearly_file

    print(f"\n📆 Consolidating year: {year}")

    quarter_strs = quarters_in_year(int(year))
    quarterly_files = []
    all_entries = []

    for q_str in quarter_strs:
        qf = QUARTERLY_DIR / f"{q_str}.md"
        if not qf.exists():
            archive_qf = MEMORY_DIR / "archive" / "quarterly" / f"{q_str}.md"
            if archive_qf.exists():
                qf = archive_qf

        if qf.exists():
            entries = parse_quarterly_entries(qf)
            print(f"  {q_str}: {len(entries)} entries")
            all_entries.extend(entries)
            quarterly_files.append(qf)

    if not all_entries:
        print(f"  No quarterly entries found for {year}. Skipping.")
        return None

    decayed = apply_yearly_decay(all_entries)
    print(f"  After decay: {len(decayed)} entries")

    yf = create_yearly_file(year, decayed, quarterly_files, dry_run=dry_run)
    cross_link_levels(yf, quarterly_files, "yearly", dry_run=dry_run)

    return yf


def main():
    parser = argparse.ArgumentParser(
        description="Monthly/quarterly/yearly memory hierarchy roll-up.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/memory_monthly_consolidation.py
  python3 scripts/memory_monthly_consolidation.py --month 2026-03
  python3 scripts/memory_monthly_consolidation.py --dry-run
  python3 scripts/memory_monthly_consolidation.py --force
        """,
    )
    parser.add_argument("--month", help="Month to process (YYYY-MM). Default: last complete month.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes")
    parser.add_argument("--force", action="store_true", help="Re-run even if files already exist")
    args = parser.parse_args()

    month_str = args.month or last_complete_month_str()
    today = datetime.now(timezone.utc)

    print(f"🗓️  Monthly Memory Consolidation — {month_str}")
    if args.dry_run:
        print("   Mode: DRY RUN\n")

    # ── Step 1: Consolidate weeklies → monthly ────────────────────────────────
    print("\n📋 Step 1: Consolidating weeklies → monthly")
    monthly_file = consolidate_month(month_str, dry_run=args.dry_run, force=args.force)

    # ── Step 2: Consolidate monthlies → quarterly (if quarter end) ────────────
    print("\n📋 Step 2: Consolidating monthlies → quarterly")
    quarter_str = quarter_for_month(month_str)

    # Check if this month closes a quarter
    if is_quarter_end_month(month_str):
        print(f"  Quarter end detected: {month_str} closes {quarter_str}")
        quarterly_file = consolidate_quarter(quarter_str, dry_run=args.dry_run, force=args.force)

        # ── Step 3: Consolidate quarterlies → yearly (if year end) ────────────
        print("\n📋 Step 3: Consolidating quarterlies → yearly")
        year = month_str[:4]
        if month_str.endswith("-12"):  # December closes the year
            print(f"  Year end detected: {year}")
            consolidate_year(year, dry_run=args.dry_run, force=args.force)
        else:
            print(f"  Not year-end (month: {month_str}), skipping yearly roll-up")
    else:
        print(f"  Not quarter-end (month: {month_str}), skipping quarterly roll-up")

    # ── Step 4: Archive old quarterlies ───────────────────────────────────────
    print(f"\n📦 Step 4: Archiving old quarterly files (keep {QUARTERLY_KEEP})")
    n_archived = archive_old_quarterlies(dry_run=args.dry_run)
    print(f"  Archived {n_archived} quarterly files")

    # ── Step 5: Update INDEX.md ───────────────────────────────────────────────
    print(f"\n📇 Step 5: Updating INDEX.md")
    update_index(dry_run=args.dry_run)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}✅ Monthly consolidation complete — {month_str}")

    # Trigger index re-embed (hierarchy changed)
    if not args.dry_run:
        try:
            from trigger_embed import trigger
            trigger(background=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
