#!/usr/bin/env python3
"""
log_memory.py — Quick CLI to log timestamped memory entries.

Creates:
  - memory/YYYY-MM-DD.md           (daily log, appended)
  - memory/entries/YYYY-MM-DD_HHMMSS_<slug>.md  (structured primitive)

Usage:
  python3 scripts/log_memory.py "Content of the memory"
  python3 scripts/log_memory.py --category technical --importance 4 --tags "snn,gradients" "Content"
  python3 scripts/log_memory.py --workspace ~/.openclaw/workspace-architect "Content"
  python3 scripts/log_memory.py --list
  python3 scripts/log_memory.py --list --category technical
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Default workspace: directory containing this script's parent (i.e. the workspace root).
# When --workspace is passed, that takes precedence.
# Agents running via cwd-based invocation can also set AGENT_WORKSPACE env var.
_DEFAULT_WORKSPACE = Path(
    os.environ.get("AGENT_WORKSPACE", "")
) if os.environ.get("AGENT_WORKSPACE") else Path(__file__).parent.parent

WORKSPACE = _DEFAULT_WORKSPACE  # may be overridden in main() before helpers use it
MEMORY_DIR = WORKSPACE / "memory"
ENTRIES_DIR = MEMORY_DIR / "entries"

CATEGORIES = ["insight", "decision", "preference", "context", "event", "technical", "relationship"]

# Keyword-based auto-detection heuristics
CATEGORY_KEYWORDS = {
    "technical": [
        "error", "bug", "code", "script", "python", "function", "import", "model",
        "architecture", "snn", "neuron", "gradient", "training", "experiment", "notebook",
        "git", "commit", "install", "config", "debug", "fix", "implement", "api", "cron",
        "memory", "cpu", "gpu", "tensor", "batch", "layer", "weight", "loss", "accuracy",
    ],
    "decision": [
        "decided", "choose", "chose", "will use", "going with", "switched to", "instead of",
        "trade-off", "tradeoff", "approach", "strategy", "plan", "direction",
    ],
    "insight": [
        "realized", "discovered", "found that", "turns out", "key insight", "breakthrough",
        "pattern", "because", "explains why", "root cause", "aha", "interesting",
    ],
    "event": [
        "completed", "finished", "started", "launched", "deployed", "failed", "succeeded",
        "milestone", "session", "conversation", "meeting", "update",
    ],
    "preference": [
        "prefer", "like", "dislike", "always", "never", "usually", "favor", "style",
        "convention", "format", "tone",
    ],
    "relationship": [
        "shael", "user", "collaborator", "agent", "bot", "team", "group", "channel",
        "asked", "said", "mentioned", "requested", "wants",
    ],
}


def auto_detect_category(content: str) -> str:
    """Simple keyword-based category detection."""
    content_lower = content.lower()
    scores = {cat: 0 for cat in CATEGORIES}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in content_lower:
                scores[cat] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "context"


def slugify(text: str, max_len: int = 40) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    return slug[:max_len].rstrip("-")


def ensure_dirs(memory_dir: Path, entries_dir: Path):
    entries_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "archive").mkdir(parents=True, exist_ok=True)


def read_frontmatter(filepath: Path) -> dict:
    """Parse YAML frontmatter from a markdown file (minimal parser, no deps)."""
    import re as _re
    content = filepath.read_text()
    m = _re.match(r"^---\n(.*?)\n---", content, _re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def list_entries(workspace: Path, category_filter: str | None = None, date_str: str | None = None):
    """List memory entries, optionally filtered by category and/or date."""
    memory_dir = workspace / "memory"
    entries_dir = memory_dir / "entries"

    if not entries_dir.exists():
        print("No memory entries found.")
        return

    if date_str:
        pattern = f"{date_str}_*.md"
    else:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        pattern = f"{today}_*.md"

    files = sorted(entries_dir.glob(pattern))
    if not files:
        print(f"No entries found for {'today' if not date_str else date_str}.")
        return

    shown = 0
    for f in files:
        fm = read_frontmatter(f)
        if category_filter and fm.get("category") != category_filter:
            continue
        ts = fm.get("timestamp", "?")
        cat = fm.get("category", "?")
        imp = fm.get("importance", "?")
        status = fm.get("status", "?")
        content = fm.get("content", "")
        tags = fm.get("tags", "")
        # Truncate long content
        preview = content[:100] + ("…" if len(content) > 100 else "")
        print(f"\n[{ts[:16]}] [{cat}] imp={imp} status={status}")
        if tags:
            print(f"  tags: {tags}")
        print(f"  {preview}")
        print(f"  → {f.relative_to(workspace)}")
        shown += 1

    if shown == 0:
        cat_msg = f" in category '{category_filter}'" if category_filter else ""
        print(f"No entries found{cat_msg}.")
    else:
        print(f"\n{shown} entr{'y' if shown == 1 else 'ies'} found.")


def log_entry(
    workspace: Path,
    content: str,
    category: str | None,
    importance: int,
    tags: list[str],
    source: str,
):
    """Create a memory entry and append to the daily log."""
    memory_dir = workspace / "memory"
    entries_dir = memory_dir / "entries"
    ensure_dirs(memory_dir, entries_dir)

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H%M%S")
    ts_full = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Auto-detect category if not provided
    if not category:
        category = auto_detect_category(content)

    # Build slug from content
    slug = slugify(content)

    # Tags as YAML list or empty list
    tags_yaml = f"[{', '.join(tags)}]" if tags else "[]"

    # --- Create structured entry file ---
    entry_filename = f"{date_str}_{time_str}_{slug}.md"
    entry_path = entries_dir / entry_filename

    # Escape content for YAML (simple approach — wrap in double quotes, escape internal quotes)
    content_escaped = content.replace('"', '\\"')

    entry_content = f"""---
primitive: memory_log
timestamp: "{ts_full}"
category: {category}
importance: {importance}
tags: {tags_yaml}
source: "{source}"
content: "{content_escaped}"
status: active
---

# Memory Entry

**{ts_full}** · `{category}` · importance {importance}/5

{content}

---
*Source: {source}*
*Tags: {', '.join(tags) if tags else 'none'}*
"""
    entry_path.write_text(entry_content)

    # --- Append to daily log ---
    daily_log = memory_dir / f"{date_str}.md"
    importance_indicator = "⚡" * min(importance, 5)

    if not daily_log.exists():
        daily_log.write_text(f"# Memory Log — {date_str}\n\n")

    with daily_log.open("a") as f:
        f.write(f"\n## {ts_full} — {category} {importance_indicator}\n\n")
        f.write(f"{content}\n\n")
        if tags:
            f.write(f"*Tags: {', '.join(tags)}*\n\n")
        f.write(f"*Source: {source}*\n\n")
        f.write(f"*Entry: `{entry_filename}`*\n\n")
        f.write("---\n")

    rel_entry = entry_path.relative_to(workspace)
    rel_daily = daily_log.relative_to(workspace)
    print(f"✓ [{category}] imp={importance} logged at {ts_full}")
    print(f"  Entry:  {rel_entry}")
    print(f"  Daily:  {rel_daily}")

    # Trigger index re-embed (debounced, background)
    try:
        from trigger_embed import trigger
        trigger(background=True)
    except Exception:
        pass  # non-critical


def main():
    parser = argparse.ArgumentParser(
        description="Log a memory entry to the daily log and create a structured primitive.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/log_memory.py "V4 experiment failed because spike-count readout killed gradients"
  python3 scripts/log_memory.py --category technical --importance 4 --tags "snn,v4" "Use membrane potential readout"
  python3 scripts/log_memory.py --workspace ~/.openclaw/workspace-architect "Designed v4 deep-analysis methodology"
  python3 scripts/log_memory.py --list
  python3 scripts/log_memory.py --list --category technical
  python3 scripts/log_memory.py --list --date 2026-03-15
        """,
    )
    parser.add_argument("content", nargs="?", help="Memory content to log")
    parser.add_argument(
        "--workspace", "-w",
        help="Workspace root to log into (default: auto-detected from script location or AGENT_WORKSPACE env var)",
    )
    parser.add_argument(
        "--category", "-c",
        choices=CATEGORIES,
        help="Category (auto-detected if omitted)",
    )
    parser.add_argument(
        "--importance", "-i",
        type=int,
        default=3,
        choices=range(1, 6),
        metavar="1-5",
        help="Importance level: 1=trivial, 5=critical (default: 3)",
    )
    parser.add_argument(
        "--tags", "-t",
        default="",
        help="Comma-separated tags, e.g. 'snn,v4,gradients'",
    )
    parser.add_argument(
        "--source", "-s",
        default="session",
        help="What triggered this memory (default: session)",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List today's memory entries",
    )
    parser.add_argument(
        "--date",
        help="Date for --list (YYYY-MM-DD, default: today)",
    )

    args = parser.parse_args()

    # Resolve workspace
    if args.workspace:
        workspace = Path(args.workspace).expanduser().resolve()
    else:
        workspace = _DEFAULT_WORKSPACE.resolve()

    if args.list:
        list_entries(
            workspace=workspace,
            category_filter=args.category,
            date_str=args.date,
        )
        return

    if not args.content:
        parser.print_help()
        sys.exit(1)

    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []
    log_entry(
        workspace=workspace,
        content=args.content,
        category=args.category,
        importance=args.importance,
        tags=tags,
        source=args.source,
    )


if __name__ == "__main__":
    main()
