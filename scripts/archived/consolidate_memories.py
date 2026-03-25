#!/usr/bin/env python3
"""
consolidate_memories.py — Daily memory consolidation script.

Reads all structured memory entries for a given day, groups by category,
generates a clean summary section in the daily log, and marks entries as
status: consolidated.

Usage:
  python3 scripts/consolidate_memories.py            # Consolidate today (main workspace)
  python3 scripts/consolidate_memories.py --date 2026-03-17
  python3 scripts/consolidate_memories.py --dry-run  # Preview only
  python3 scripts/consolidate_memories.py --check    # Exit 0 if nothing to do, 1 if consolidation needed
  python3 scripts/consolidate_memories.py --workspace ~/.openclaw/workspace-architect
  python3 scripts/consolidate_memories.py --all-agents  # Consolidate all 4 workspaces
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_WORKSPACE = Path(__file__).parent.parent

AGENT_WORKSPACES = {
    "main":      Path(os.path.expanduser("~/.openclaw/workspace")),
    "architect": Path(os.path.expanduser("~/.openclaw/workspace-architect")),
    "critic":    Path(os.path.expanduser("~/.openclaw/workspace-critic")),
    "builder":   Path(os.path.expanduser("~/.openclaw/workspace-builder")),
}

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


def get_entries_for_date(workspace: Path, date_str: str) -> list[tuple[Path, dict]]:
    """Return list of (path, frontmatter) for entries matching the date."""
    entries_dir = workspace / "memory" / "entries"
    if not entries_dir.exists():
        return []
    files = sorted(entries_dir.glob(f"{date_str}_*.md"))
    results = []
    for f in files:
        fm, _ = parse_frontmatter(f)
        results.append((f, fm))
    return results


def check_needs_consolidation(workspace: Path, date_str: str) -> bool:
    """Return True if there are active (non-consolidated) entries for this date."""
    entries = get_entries_for_date(workspace, date_str)
    return any(fm.get("status", "active") == "active" for _, fm in entries)


def consolidate(workspace: Path, date_str: str, dry_run: bool = False, label: str = "") -> int:
    """
    Consolidate entries for the given date in workspace. Returns count of processed entries.
    """
    memory_dir = workspace / "memory"
    entries_dir = memory_dir / "entries"
    prefix = f"[{label}] " if label else ""

    entries = get_entries_for_date(workspace, date_str)
    if not entries:
        print(f"{prefix}No memory entries found for {date_str}.")
        return 0

    active = [(p, fm) for p, fm in entries if fm.get("status", "active") == "active"]
    if not active:
        print(f"{prefix}All entries for {date_str} are already consolidated.")
        return 0

    print(f"{prefix}Found {len(active)} active entr{'y' if len(active) == 1 else 'ies'} for {date_str}.")

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
        print(f"\n{prefix}=== DRY RUN: Would append to daily log ===")
        print(summary_text)
        print(f"{prefix}=== Would mark {len(active)} entries as 'consolidated' ===")
        return len(active)

    # Append to daily log
    daily_log = memory_dir / f"{date_str}.md"
    if not daily_log.exists():
        daily_log.write_text(f"# Memory Log — {date_str}\n\n")

    with daily_log.open("a") as f:
        f.write(summary_text)

    # Mark entries as consolidated
    for path, fm in active:
        update_frontmatter_status(path, "consolidated")

    rel_log = daily_log.relative_to(workspace) if daily_log.is_relative_to(workspace) else daily_log
    print(f"{prefix}✓ Consolidated {len(active)} entries into {rel_log}")
    print(f"{prefix}✓ Marked {len(active)} entries as 'consolidated'")

    # Trigger index re-embed (debounced, background)
    try:
        from trigger_embed import trigger
        trigger(background=True)
    except Exception:
        pass  # non-critical

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
  python3 scripts/consolidate_memories.py --workspace ~/.openclaw/workspace-architect
  python3 scripts/consolidate_memories.py --all-agents
  python3 scripts/consolidate_memories.py --all-agents --dry-run
        """,
    )
    parser.add_argument(
        "--date",
        help="Date to consolidate (YYYY-MM-DD, default: today UTC)",
    )
    parser.add_argument(
        "--workspace", "-w",
        help="Workspace root to consolidate (default: main workspace)",
    )
    parser.add_argument(
        "--all-agents",
        action="store_true",
        help="Consolidate all 4 agent workspaces (main + architect + critic + builder)",
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

    if args.all_agents:
        if args.check:
            needs = any(
                check_needs_consolidation(ws, date_str)
                for ws in AGENT_WORKSPACES.values()
            )
            if needs:
                print(f"Consolidation needed for {date_str} (some agents have active entries).")
                sys.exit(1)
            else:
                print(f"Nothing to consolidate for {date_str}.")
                sys.exit(0)

        total = 0
        for agent_name, ws in AGENT_WORKSPACES.items():
            print(f"\n── Agent: {agent_name} ({ws}) ──")
            total += consolidate(ws, date_str, dry_run=args.dry_run, label=agent_name)
        print(f"\n✓ Total across all agents: {total} entries consolidated")
        return

    # Single workspace mode
    if args.workspace:
        workspace = Path(args.workspace).expanduser().resolve()
    else:
        workspace = _SCRIPT_WORKSPACE.resolve()

    if args.check:
        needs = check_needs_consolidation(workspace, date_str)
        if needs:
            print(f"Consolidation needed for {date_str}.")
            sys.exit(1)
        else:
            print(f"Nothing to consolidate for {date_str}.")
            sys.exit(0)

    consolidate(workspace, date_str, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
