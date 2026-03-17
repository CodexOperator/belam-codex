#!/usr/bin/env python3
"""
consolidate_memories.py — Daily memory consolidation script.

Reads all structured memory entries for a given day, groups by category,
generates a clean summary section in the daily log, and marks entries as
status: consolidated.

Usage:
  python3 scripts/consolidate_memories.py            # Consolidate today
  python3 scripts/consolidate_memories.py --date 2026-03-17
  python3 scripts/consolidate_memories.py --dry-run  # Preview only
  python3 scripts/consolidate_memories.py --check    # Exit 0 if nothing to do, 1 if consolidation needed
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
MEMORY_DIR = WORKSPACE / "memory"
ENTRIES_DIR = MEMORY_DIR / "entries"

CATEGORIES = ["insight", "decision", "preference", "context", "event", "technical", "relationship"]

CATEGORY_ICONS = {
    "insight": "💡",
    "decision": "⚖️",
    "preference": "⭐",
    "context": "📍",
    "event": "📅",
    "technical": "🔧",
    "relationship": "🤝",
}


def parse_frontmatter(filepath: Path) -> tuple[dict, str]:
    """Parse YAML frontmatter and return (frontmatter_dict, body_text)."""
    text = filepath.read_text()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)", text, re.DOTALL)
    if not m:
        return {}, text

    fm_raw = m.group(1)
    body = m.group(2)
    fm = {}
    for line in fm_raw.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            v = v.strip().strip('"').strip("'")
            fm[k.strip()] = v
    # Parse tags list
    if "tags" in fm:
        tags_raw = fm["tags"].strip("[]")
        fm["tags"] = [t.strip().strip('"').strip("'") for t in tags_raw.split(",") if t.strip()]
    else:
        fm["tags"] = []
    return fm, body


def update_frontmatter_status(filepath: Path, new_status: str) -> None:
    """Update only the status field in YAML frontmatter of a file."""
    text = filepath.read_text()
    updated = re.sub(
        r"^status:.*$",
        f"status: {new_status}",
        text,
        flags=re.MULTILINE,
    )
    filepath.write_text(updated)


def get_entries_for_date(date_str: str) -> list[tuple[Path, dict]]:
    """Return list of (path, frontmatter) for entries matching the date."""
    if not ENTRIES_DIR.exists():
        return []
    files = sorted(ENTRIES_DIR.glob(f"{date_str}_*.md"))
    results = []
    for f in files:
        fm, _ = parse_frontmatter(f)
        results.append((f, fm))
    return results


def check_needs_consolidation(date_str: str) -> bool:
    """Return True if there are active (non-consolidated) entries for this date."""
    entries = get_entries_for_date(date_str)
    return any(fm.get("status", "active") == "active" for _, fm in entries)


def consolidate(date_str: str, dry_run: bool = False) -> int:
    """
    Consolidate entries for the given date. Returns count of processed entries.
    """
    entries = get_entries_for_date(date_str)
    if not entries:
        print(f"No memory entries found for {date_str}.")
        return 0

    active = [(p, fm) for p, fm in entries if fm.get("status", "active") == "active"]
    if not active:
        print(f"All entries for {date_str} are already consolidated.")
        return 0

    print(f"Found {len(active)} active entr{'y' if len(active) == 1 else 'ies'} for {date_str}.")

    # Group by category
    grouped: dict[str, list[dict]] = {cat: [] for cat in CATEGORIES}
    other = []
    for path, fm in active:
        cat = fm.get("category", "context")
        if cat in grouped:
            grouped[cat].append({**fm, "_path": path})
        else:
            other.append({**fm, "_path": path})

    # Build consolidated summary
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"\n## Consolidated Entries — {date_str}",
        f"\n*Generated at {now_ts} — {len(active)} entries*\n",
    ]

    for cat in CATEGORIES:
        entries_in_cat = grouped.get(cat, [])
        if not entries_in_cat:
            continue
        icon = CATEGORY_ICONS.get(cat, "•")
        lines.append(f"\n### {icon} {cat.title()} ({len(entries_in_cat)})\n")
        for e in entries_in_cat:
            imp = e.get("importance", "3")
            content = e.get("content", "").replace('\\"', '"')
            tags = e.get("tags", [])
            imp_stars = "★" * int(imp) + "☆" * (5 - int(imp))
            lines.append(f"- **[{imp_stars}]** {content}")
            if tags:
                lines.append(f"  *tags: {', '.join(tags)}*")
        lines.append("")

    if other:
        lines.append(f"\n### • Other ({len(other)})\n")
        for e in other:
            content = e.get("content", "").replace('\\"', '"')
            lines.append(f"- {content}")
        lines.append("")

    lines.append("---\n")
    summary_text = "\n".join(lines)

    if dry_run:
        print("\n=== DRY RUN: Would append to daily log ===")
        print(summary_text)
        print(f"=== Would mark {len(active)} entries as 'consolidated' ===")
        return len(active)

    # Append to daily log
    daily_log = MEMORY_DIR / f"{date_str}.md"
    if not daily_log.exists():
        daily_log.write_text(f"# Memory Log — {date_str}\n\n")

    with daily_log.open("a") as f:
        f.write(summary_text)

    # Mark entries as consolidated
    for path, fm in active:
        update_frontmatter_status(path, "consolidated")

    print(f"✓ Consolidated {len(active)} entries into {daily_log.relative_to(WORKSPACE)}")
    print(f"✓ Marked {len(active)} entries as 'consolidated'")
    return len(active)


def main():
    parser = argparse.ArgumentParser(
        description="Consolidate daily memory entries into a summary section.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/consolidate_memories.py
  python3 scripts/consolidate_memories.py --date 2026-03-17
  python3 scripts/consolidate_memories.py --dry-run
  python3 scripts/consolidate_memories.py --check
        """,
    )
    parser.add_argument(
        "--date",
        help="Date to consolidate (YYYY-MM-DD, default: today UTC)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be consolidated without writing",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 0 if nothing to consolidate, 1 if consolidation is needed",
    )

    args = parser.parse_args()

    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if args.check:
        needs = check_needs_consolidation(date_str)
        if needs:
            print(f"Consolidation needed for {date_str}.")
            sys.exit(1)
        else:
            print(f"Nothing to consolidate for {date_str}.")
            sys.exit(0)

    consolidate(date_str, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
