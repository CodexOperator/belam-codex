#!/usr/bin/env python3
"""
Embed primitive index into AGENTS.md and MEMORY.md bootstrap files.

Generates:
- AGENTS.md section: primitives with usage guidance (when/why to reference each)
- MEMORY.md section: structural YAML index of all primitives

Run: python3 scripts/embed_primitives.py [--dry-run]
Cron: after consolidation or on demand
"""

import os
import sys
import re
import yaml
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE = Path(os.environ.get("WORKSPACE", Path.home() / ".openclaw" / "workspace"))
AGENTS_FILE = WORKSPACE / "AGENTS.md"
MEMORY_FILE = WORKSPACE / "MEMORY.md"

PRIMITIVE_DIRS = {
    "lessons": WORKSPACE / "lessons",
    "decisions": WORKSPACE / "decisions",
    "tasks": WORKSPACE / "tasks",
    "projects": WORKSPACE / "projects",
}

MEMORY_DIR = WORKSPACE / "memory"
MEMORY_HIERARCHY_DIRS = {
    "weekly": MEMORY_DIR / "weekly",
    "monthly": MEMORY_DIR / "monthly",
    "quarterly": MEMORY_DIR / "quarterly",
    "yearly": MEMORY_DIR / "yearly",
}

# Markers for auto-generated sections
AGENTS_START = "<!-- BEGIN:PRIMITIVES -->"
AGENTS_END = "<!-- END:PRIMITIVES -->"
MEMORY_START = "<!-- BEGIN:PRIMITIVE_INDEX -->"
MEMORY_END = "<!-- END:PRIMITIVE_INDEX -->"
MEMORY_HIER_START = "<!-- BEGIN:MEMORY_HIERARCHY -->"
MEMORY_HIER_END = "<!-- END:MEMORY_HIERARCHY -->"
MAX_BOOTSTRAP_CHARS = 15000  # Budget for MEMORY.md (index + hierarchy only, no embedded content)
MAX_AGENTS_CHARS = 18000  # AGENTS.md budget


def parse_frontmatter(filepath: Path) -> dict:
    """Extract YAML frontmatter from a markdown file."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return {}
    
    if not text.startswith("---"):
        return {}
    
    end = text.find("---", 3)
    if end == -1:
        return {}
    
    try:
        return yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return {}


def extract_title(filepath: Path) -> str:
    """Extract the first H1/H2 heading from a markdown file."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return filepath.stem
    
    # Skip frontmatter
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:]
    
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
        if line.startswith("## "):
            return line[3:].strip()
    
    return filepath.stem.replace("-", " ").title()


def load_all_primitives() -> dict:
    """Load all primitives organized by type."""
    primitives = {}
    for ptype, pdir in PRIMITIVE_DIRS.items():
        if not pdir.exists():
            continue
        items = []
        for f in sorted(pdir.glob("*.md")):
            fm = parse_frontmatter(f)
            title = extract_title(f)
            items.append({
                "file": f.stem,
                "path": f"{ptype}/{f.name}",
                "title": title,
                "frontmatter": fm,
            })
        primitives[ptype] = items
    return primitives


def build_agents_section(primitives: dict) -> str:
    """Build compact AGENTS.md primitives section with usage guidance."""
    lines = []
    lines.append("")
    lines.append("## Workspace Primitives")
    lines.append("")
    lines.append("Knowledge files. Read with `Read` when relevant. YAML frontmatter + markdown body.")
    lines.append("")

    # Projects — compact table-like format
    if "projects" in primitives:
        lines.append("### Projects")
        for p in primitives["projects"]:
            fm = p["frontmatter"]
            status = fm.get("status", "?")
            tags = fm.get("tags", [])
            tag_str = ",".join(tags) if isinstance(tags, list) else str(tags)
            lines.append(f"- `{p['path']}` — {p['title']} [{status}] [{tag_str}]")
        lines.append("")

    # Tasks
    if "tasks" in primitives:
        lines.append("### Tasks")
        lines.append("_Read when: checking open/blocked/in-pipeline work._")
        for t in primitives["tasks"]:
            fm = t["frontmatter"]
            status = fm.get("status", "?")
            priority = fm.get("priority", "?")
            deps = fm.get("depends_on", [])
            dep_str = f" →{','.join(deps)}" if deps else ""
            title = _short_title(t["title"])
            lines.append(f"- `{t['path']}` — {title} [{status}/{priority}]{dep_str}")
        lines.append("")

    # Decisions
    if "decisions" in primitives:
        lines.append("### Decisions")
        lines.append("_Read when: making architectural choices._")
        for d in primitives["decisions"]:
            fm = d["frontmatter"]
            skill = fm.get("skill", "")
            skill_str = f" (skill:{skill})" if skill else ""
            tags = fm.get("tags", [])
            tag_str = ",".join(tags[:3]) if isinstance(tags, list) else str(tags)
            title = _short_title(d["title"])
            lines.append(f"- `{d['path']}` — {title}{skill_str} [{tag_str}]")
        lines.append("")

    # Lessons
    if "lessons" in primitives:
        lines.append("### Lessons")
        lines.append("_Read when: encountering problems or before making changes._")
        for l in primitives["lessons"]:
            fm = l["frontmatter"]
            confidence = fm.get("confidence", "?")
            tags = fm.get("tags", [])
            tag_str = ",".join(tags[:3]) if isinstance(tags, list) else str(tags)
            title = _short_title(l["title"])
            lines.append(f"- `{l['path']}` — {title} [{confidence}] [{tag_str}]")
        lines.append("")

    return "\n".join(lines)


def _short_title(title: str) -> str:
    """Strip common prefixes from titles for compact display."""
    for prefix in ["Lesson: ", "Decision: ", "Decision — "]:
        if title.startswith(prefix):
            title = title[len(prefix):]
    # Truncate very long titles
    if len(title) > 60:
        title = title[:57] + "..."
    return title


def build_memory_section(primitives: dict) -> str:
    """Build compact ASCII tree primitive index for MEMORY.md."""
    lines = []
    lines.append("")
    lines.append("## Primitive Index")
    lines.append("")
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    for ptype, items in primitives.items():
        count = len(items)
        lines.append(f"{ptype}/ ({count})")
        for i, item in enumerate(items):
            fm = item["frontmatter"]
            is_last = (i == count - 1)
            prefix = "└─" if is_last else "├─"

            # Build compact metadata
            meta_parts = []
            if ptype == "tasks":
                status = fm.get("status", "?")
                priority = fm.get("priority", "?")
                meta_parts.append(f"{status}/{priority}")
                deps = fm.get("depends_on", [])
                if deps:
                    meta_parts.append(f"→{','.join(deps)}")
            elif ptype == "projects":
                meta_parts.append(fm.get("status", "?"))
            elif ptype == "decisions":
                skill = fm.get("skill", "")
                if skill:
                    meta_parts.append(f"skill:{skill}")
            elif ptype == "lessons":
                conf = fm.get("confidence", "")
                if conf:
                    meta_parts.append(conf)

            tags = fm.get("tags", [])
            if tags and isinstance(tags, list):
                meta_parts.append(f"[{','.join(tags[:4])}]")

            meta_str = "  ".join(meta_parts)
            title = _short_title(item["title"])
            lines.append(f"  {prefix} {item['file']}  {title}  {meta_str}")
        lines.append("")

    lines.append(f"_Updated: {ts}_")
    lines.append("")
    return "\n".join(lines)


def load_memory_hierarchy() -> dict:
    """Load memory hierarchy files (weekly, monthly, quarterly, yearly) as primitives."""
    hierarchy = {}
    for level, level_dir in MEMORY_HIERARCHY_DIRS.items():
        if not level_dir.exists():
            hierarchy[level] = []
            continue
        items = []
        # Match appropriate patterns per level
        patterns = {
            "weekly": "????-W??.md",
            "monthly": "????-??.md",
            "quarterly": "????-Q?.md",
            "yearly": "????.md",
        }
        for f in sorted(level_dir.glob(patterns.get(level, "*.md")), reverse=True):
            fm = parse_frontmatter(f)
            title = fm.get("title", "")
            if not title:
                title = extract_title(f)

            # Extract key topics from tags or content
            tags = fm.get("tags", [])
            if not tags:
                # Fallback: scan for topic keywords in file
                try:
                    text = f.read_text(encoding="utf-8")[:2000]
                    tags = _detect_topic_tags(text)
                except Exception:
                    tags = []

            period = fm.get("period", f.stem)
            entry_count = fm.get("entry_count", None)
            if entry_count is None:
                # Count entries from file
                try:
                    text = f.read_text(encoding="utf-8")
                    entry_count = text.count("- **[")
                except Exception:
                    entry_count = 0

            items.append({
                "file": f.stem,
                "path": f"memory/{level}/{f.name}",
                "title": title,
                "period": period,
                "tags": tags if isinstance(tags, list) else [],
                "entry_count": entry_count,
                "frontmatter": fm,
            })
        hierarchy[level] = items
    return hierarchy


def _detect_topic_tags(text: str) -> list:
    """Detect topic tags from text content."""
    text_lower = text.lower()
    topics = {
        "snn": ["snn", "neuron", "spike", "membrane"],
        "infrastructure": ["agent", "orchestrat", "pipeline", "cron"],
        "gpu": ["gpu", "cuda", "t4", "colab"],
        "trading": ["financial", "btc", "trading", "sharpe"],
        "memory": ["memory", "consolidat", "knowledge"],
    }
    found = []
    for tag, keywords in topics.items():
        if any(kw in text_lower for kw in keywords):
            found.append(tag)
    return found[:4]


def _count_daily_files() -> tuple[int, list[str]]:
    """Count active daily files and return (count, [date_strings])."""
    daily_files = sorted(MEMORY_DIR.glob("????-??-??.md"))
    dates = [f.stem for f in daily_files]
    return len(daily_files), dates


def build_memory_hierarchy_section(hierarchy: dict) -> str:
    """Build compact ASCII tree memory hierarchy for MEMORY.md."""
    lines = []
    lines.append("")
    lines.append("## Memory Hierarchy")
    lines.append("")
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    # Daily summary
    daily_count, daily_dates = _count_daily_files()

    # Indexed entries count
    entries_dir = MEMORY_DIR / "entries"
    entry_count = len(list(entries_dir.glob("*.md"))) if entries_dir.exists() else 0

    lines.append("```")
    lines.append(f"Memory ({ts})")
    if daily_dates:
        lines.append(f"├── daily/      {daily_count} active  {daily_dates[0]} → {daily_dates[-1]}")
    else:
        lines.append(f"├── daily/      0 active")
    lines.append(f"├── entries/    {entry_count} indexed")

    levels = ["weekly", "monthly", "quarterly", "yearly"]
    for li, level in enumerate(levels):
        items = hierarchy.get(level, [])
        is_last_level = (li == len(levels) - 1)
        branch = "└──" if is_last_level else "├──"
        if not items:
            lines.append(f"{branch} {level}/    —")
        elif len(items) == 1:
            item = items[0]
            tags_str = f"  [{','.join(item['tags'])}]" if item['tags'] else ""
            lines.append(f"{branch} {level}/")
            sub_branch = "    └─" if is_last_level else "│   └─"
            lines.append(f"{sub_branch} {item['file']}  {item['period']}{tags_str}")
        else:
            lines.append(f"{branch} {level}/")
            for ii, item in enumerate(items):
                tags_str = f"  [{','.join(item['tags'])}]" if item['tags'] else ""
                is_last_item = (ii == len(items) - 1)
                if is_last_level:
                    sub_branch = "    └─" if is_last_item else "    ├─"
                else:
                    sub_branch = "│   └─" if is_last_item else "│   ├─"
                lines.append(f"{sub_branch} {item['file']}  {item['period']}{tags_str}")

    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def inject_section(filepath, start_marker: str, end_marker: str, content: str, max_chars: int, existing_text: str = None) -> str:
    """Inject content between markers in a file, respecting char budget.
    If existing_text is provided, use it instead of reading from filepath."""
    if existing_text is not None:
        text = existing_text
    else:
        try:
            text = filepath.read_text(encoding="utf-8")
        except FileNotFoundError:
            text = ""
    
    # Remove existing section if present
    pattern = re.compile(
        re.escape(start_marker) + r".*?" + re.escape(end_marker),
        re.DOTALL
    )
    text = pattern.sub("", text).rstrip()
    
    # Build new section
    section = f"\n{start_marker}\n{content}\n{end_marker}\n"
    
    # Check budget
    new_text = text + section
    if len(new_text) > max_chars:
        # Truncate content to fit
        available = max_chars - len(text) - len(start_marker) - len(end_marker) - 10
        if available > 200:
            content = content[:available] + "\n\n_[truncated — run `belam primitives` for full list]_"
            section = f"\n{start_marker}\n{content}\n{end_marker}\n"
            new_text = text + section
        else:
            print(f"  ⚠ Not enough space in {filepath.name} ({len(text)} chars used)")
            return text
    
    return new_text


def main():
    dry_run = "--dry-run" in sys.argv
    
    print("📦 Embedding primitives into bootstrap files...")
    
    # Load all primitives
    primitives = load_all_primitives()
    total = sum(len(v) for v in primitives.values())
    print(f"  Found {total} primitives across {len(primitives)} types")
    
    # Load memory hierarchy
    hierarchy = load_memory_hierarchy()
    hier_total = sum(len(v) for v in hierarchy.values())
    print(f"  Found {hier_total} memory hierarchy files across {len(hierarchy)} levels")
    
    # Build sections
    agents_section = build_agents_section(primitives)
    memory_section = build_memory_section(primitives)
    memory_hier_section = build_memory_hierarchy_section(hierarchy)
    
    # Inject into AGENTS.md
    agents_text = inject_section(AGENTS_FILE, AGENTS_START, AGENTS_END, agents_section, MAX_AGENTS_CHARS)
    print(f"  AGENTS.md: {len(agents_text)} chars")
    
    # Inject into MEMORY.md (primitive index + memory hierarchy only — no embedded content)
    memory_text = inject_section(MEMORY_FILE, MEMORY_START, MEMORY_END, memory_section, MAX_BOOTSTRAP_CHARS)
    memory_text = inject_section(
        None, MEMORY_HIER_START, MEMORY_HIER_END, memory_hier_section, MAX_BOOTSTRAP_CHARS,
        existing_text=memory_text
    )
    print(f"  MEMORY.md: {len(memory_text)} chars")
    
    if dry_run:
        print("\n--- AGENTS.md (preview) ---")
        print(agents_text[-2000:] if len(agents_text) > 2000 else agents_text)
        print("\n--- MEMORY.md (preview) ---")
        print(memory_text[-3000:] if len(memory_text) > 3000 else memory_text)
        print("\n  [dry run — no files written]")
    else:
        AGENTS_FILE.write_text(agents_text, encoding="utf-8")
        MEMORY_FILE.write_text(memory_text, encoding="utf-8")
        print("  ✅ Written")


if __name__ == "__main__":
    main()
