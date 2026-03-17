#!/usr/bin/env python3
"""
weekly_knowledge_sync.py — Weekly knowledge graph sync.

Processes the past week's lessons and memory entries into the knowledge/ graph.
Runs weekly (Monday 3 AM UTC via cron) but is safe to run any time.

Usage:
  python3 scripts/weekly_knowledge_sync.py            # Sync past 7 days (main workspace)
  python3 scripts/weekly_knowledge_sync.py --week 2026-03-10  # Specific week start
  python3 scripts/weekly_knowledge_sync.py --dry-run  # Preview only
  python3 scripts/weekly_knowledge_sync.py --all-agents  # Sync across all 4 agent workspaces
"""

import argparse
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

WORKSPACE = Path(__file__).parent.parent
MEMORY_DIR = WORKSPACE / "memory"
ENTRIES_DIR = MEMORY_DIR / "entries"
LESSONS_DIR = WORKSPACE / "lessons"
KNOWLEDGE_DIR = WORKSPACE / "knowledge"
ARCHIVE_MEMORY_DIR = MEMORY_DIR / "archive"
ARCHIVE_ENTRIES_DIR = ARCHIVE_MEMORY_DIR / "entries"

# All agent workspaces for --all-agents mode
AGENT_WORKSPACES = {
    "main":      Path(os.path.expanduser("~/.openclaw/workspace")),
    "architect": Path(os.path.expanduser("~/.openclaw/workspace-architect")),
    "critic":    Path(os.path.expanduser("~/.openclaw/workspace-critic")),
    "builder":   Path(os.path.expanduser("~/.openclaw/workspace-builder")),
}

CATEGORIES = ["insight", "decision", "preference", "context", "event", "technical", "relationship"]

# Topic detection: maps keyword patterns to knowledge file slugs/topics
TOPIC_KEYWORDS = {
    "snn-architecture": [
        "snn", "neuron", "leaky", "synaptic", "alpha", "spike", "membrane", "potential",
        "snntorch", "refractory", "timestep", "beta", "threshold", "readout", "lif",
        "spiking neural", "integrate-and-fire", "snns",
    ],
    "financial-encoding": [
        "delta encoding", "rate coding", "population coding", "candle", "btc", "bitcoin",
        "financial", "price", "ohlcv", "technical indicator", "rsi", "macd", "orderbook",
        "market", "trading", "prediction market", "forex", "crypto", "stock", "equity",
    ],
    "gpu-optimization": [
        "gpu", "cuda", "tpu", "a100", "t4", "colab", "training time", "batch size",
        "mixed precision", "fp16", "throughput", "parallelism", "memory bandwidth",
        "compute", "accelerator", "tensor core",
    ],
    "agent-coordination": [
        "agent", "subagent", "sub-agent", "orchestrat", "coordinator", "heartbeat",
        "session", "openclaw", "cron", "telegram", "bot", "channel", "spawn",
        "multi-agent", "collaboration", "filesystem", "primitive",
    ],
    "experiment-methodology": [
        "experiment", "hypothesis", "result", "accuracy", "loss", "metric", "sharpe",
        "backtest", "validation", "overfitting", "cross-validation", "fold", "baseline",
        "ablation", "benchmark", "evaluation", "pipeline", "notebook", "v1", "v2", "v3", "v4",
    ],
    "ml-architecture": [
        "lstm", "transformer", "attention", "neural network", "deep learning",
        "gradient", "backprop", "optimizer", "adam", "learning rate", "regularization",
        "dropout", "batch norm", "residual", "encoder", "decoder", "embedding",
    ],
    "research-workflow": [
        "lesson", "insight", "decision", "knowledge", "memory", "consolidat",
        "document", "commit", "git", "report", "analysis", "brief", "tracker",
        "techniques", "workflow", "methodology", "process",
    ],
}

TOPIC_NAMES = {
    "snn-architecture": "SNN Architecture Patterns",
    "financial-encoding": "Financial Data Encoding",
    "gpu-optimization": "GPU & Compute Optimization",
    "agent-coordination": "Agent Coordination Patterns",
    "experiment-methodology": "Experiment Methodology",
    "ml-architecture": "ML Architecture Patterns",
    "research-workflow": "Research Workflow",
}


def parse_frontmatter(filepath: Path) -> tuple[dict, str]:
    """Parse YAML frontmatter and return (frontmatter_dict, body_text)."""
    try:
        text = filepath.read_text()
    except Exception:
        return {}, ""
    m = re.match(r"^---\n(.*?)\n---\n?(.*)", text, re.DOTALL)
    if not m:
        return {}, text
    fm_raw = m.group(1)
    body = m.group(2)
    fm = {}
    for line in fm_raw.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            v_stripped = v.strip().strip('"').strip("'")
            fm[k.strip()] = v_stripped
    # Parse tags/list fields
    for key in ("tags", "applies_to", "sources", "related"):
        if key in fm:
            raw = fm[key].strip("[]")
            fm[key] = [t.strip().strip('"').strip("'") for t in raw.split(",") if t.strip()]
        else:
            fm[key] = []
    return fm, body


def detect_topics(text: str) -> list[str]:
    """Detect which knowledge topics this text is relevant to."""
    text_lower = text.lower()
    matched = []
    for topic_slug, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                matched.append(topic_slug)
                break
    return matched if matched else ["research-workflow"]  # Default fallback


def slugify(text: str) -> str:
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug.strip("-")[:50].rstrip("-")


def load_knowledge_file(slug: str) -> tuple[dict, list[str]]:
    """Load an existing knowledge file, returning (frontmatter, findings_lines)."""
    kf = KNOWLEDGE_DIR / f"{slug}.md"
    if not kf.exists():
        return {}, []
    fm, body = parse_frontmatter(kf)
    # Extract existing key findings
    findings = []
    in_findings = False
    for line in body.splitlines():
        if re.match(r"^## Key Findings", line):
            in_findings = True
            continue
        if in_findings:
            if re.match(r"^## ", line):
                break
            if line.strip():
                findings.append(line)
    return fm, findings


def write_knowledge_file(
    slug: str,
    topic_name: str,
    tags: list[str],
    findings: list[str],
    sources: list[str],
    related: list[str],
    created: str,
    dry_run: bool = False,
) -> str:
    """Write (or update) a knowledge graph file."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    kf = KNOWLEDGE_DIR / f"{slug}.md"

    # Deduplicate
    tags = sorted(set(tags))
    sources = sorted(set(sources))
    related = sorted(set(r for r in related if r != slug))
    # Deduplicate findings (exact match)
    seen = set()
    unique_findings = []
    for f in findings:
        key = f.strip().lower()
        if key not in seen:
            seen.add(key)
            unique_findings.append(f)

    tags_yaml = "[" + ", ".join(tags) + "]"
    sources_yaml = "[" + ", ".join(sources) + "]"
    related_yaml = "[" + ", ".join(related) + "]"

    findings_text = "\n".join(unique_findings) if unique_findings else "*(No findings yet)*"

    content = f"""---
topic: {topic_name}
tags: {tags_yaml}
created: {created}
updated: {today}
sources: {sources_yaml}
related: {related_yaml}
---

# {topic_name}

## Key Findings

{findings_text}

## Notes

*(Add contextual notes here as patterns emerge)*
"""

    if dry_run:
        print(f"  [DRY RUN] Would write: knowledge/{slug}.md ({len(unique_findings)} findings)")
        return str(kf)

    KNOWLEDGE_DIR.mkdir(exist_ok=True)
    kf.write_text(content)
    return str(kf)


def load_week_lessons(week_start: datetime) -> list[tuple[Path, dict, str]]:
    """Load lessons created in the past week."""
    if not LESSONS_DIR.exists():
        return []
    week_end = week_start + timedelta(days=7)
    results = []
    for f in sorted(LESSONS_DIR.glob("*.md")):
        fm, body = parse_frontmatter(f)
        date_str = fm.get("date", "")
        if not date_str:
            continue
        try:
            lesson_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if week_start <= lesson_date < week_end:
            results.append((f, fm, body))
    return results


def load_week_memory_entries(week_start: datetime, workspace: Path | None = None) -> list[tuple[Path, dict]]:
    """Load memory entries created in the past week from a specific workspace (default: main)."""
    entries_dir = (workspace / "memory" / "entries") if workspace else ENTRIES_DIR
    if not entries_dir.exists():
        return []
    week_end = week_start + timedelta(days=7)
    results = []
    for f in sorted(entries_dir.glob("*.md")):
        fm, _ = parse_frontmatter(f)
        ts_str = fm.get("timestamp", "")
        if not ts_str:
            continue
        try:
            ts = datetime.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if week_start <= ts < week_end:
            results.append((f, fm))
    return results


def load_all_agent_memory_entries(week_start: datetime) -> list[tuple[Path, dict, str]]:
    """Load memory entries from ALL agent workspaces; returns (path, fm, agent_name)."""
    results = []
    for agent_name, ws in AGENT_WORKSPACES.items():
        for path, fm in load_week_memory_entries(week_start, workspace=ws):
            results.append((path, fm, agent_name))
    return results


def generate_cross_agent_synthesis(
    all_entries: list[tuple[Path, dict, str]],
    week_start: datetime,
    dry_run: bool = False,
) -> str:
    """
    Generate a cross-agent synthesis section as markdown text.
    Looks for patterns repeated across multiple agents.
    """
    from collections import Counter
    week_end = week_start + timedelta(days=7)
    week_str = week_start.strftime("%Y-%m-%d")

    # Group by agent
    by_agent: dict[str, list[dict]] = defaultdict(list)
    for path, fm, agent_name in all_entries:
        by_agent[agent_name].append(fm)

    # Find common tags across agents
    tag_agents: dict[str, set] = defaultdict(set)
    for path, fm, agent_name in all_entries:
        for tag in fm.get("tags", []):
            tag_agents[tag].add(agent_name)

    cross_agent_tags = {
        tag: agents
        for tag, agents in tag_agents.items()
        if len(agents) >= 2
    }

    # Find high-importance entries (importance >= 4) across all agents
    high_importance = [
        (fm.get("content", "").replace('\\"', '"'), agent_name)
        for path, fm, agent_name in all_entries
        if int(fm.get("importance", "3")) >= 4
    ]

    lines = [
        f"\n## Cross-Agent Weekly Synthesis — {week_str}\n",
        f"*{len(all_entries)} total entries across {len(by_agent)} agents*\n",
    ]

    # Per-agent entry counts
    lines.append("\n### Agent Activity\n")
    for agent_name in sorted(by_agent.keys()):
        entries = by_agent[agent_name]
        lines.append(f"- **{agent_name.title()}**: {len(entries)} entries")
    lines.append("")

    # Cross-agent patterns
    if cross_agent_tags:
        lines.append("\n### Shared Themes (across multiple agents)\n")
        for tag, agents in sorted(cross_agent_tags.items(), key=lambda x: -len(x[1])):
            agent_list = ", ".join(sorted(agents))
            lines.append(f"- `{tag}` — mentioned by: {agent_list}")
        lines.append("")

    # High-importance entries
    if high_importance:
        lines.append("\n### High-Importance Entries (imp ≥ 4)\n")
        for content, agent_name in high_importance[:10]:
            preview = content[:120] + ("…" if len(content) > 120 else "")
            lines.append(f"- **[{agent_name}]** {preview}")
        lines.append("")

    lines.append("---\n")
    return "\n".join(lines)


def archive_old_files(cutoff: datetime, dry_run: bool = False) -> int:
    """Archive daily memory logs and entries older than cutoff."""
    archived = 0

    # Archive daily log files
    if MEMORY_DIR.exists():
        for f in MEMORY_DIR.glob("????-??-??.md"):
            try:
                file_date = datetime.strptime(f.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if file_date < cutoff:
                yyyy_mm = file_date.strftime("%Y-%m")
                dest_dir = ARCHIVE_MEMORY_DIR / yyyy_mm
                if not dry_run:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(f), str(dest_dir / f.name))
                else:
                    print(f"  [DRY RUN] Would archive: memory/{f.name} → memory/archive/{yyyy_mm}/")
                archived += 1

    # Archive consolidated entry files
    if ENTRIES_DIR.exists():
        for f in sorted(ENTRIES_DIR.glob("*.md")):
            fm, _ = parse_frontmatter(f)
            status = fm.get("status", "active")
            if status not in ("consolidated", "archived"):
                continue
            ts_str = fm.get("timestamp", "")
            if not ts_str:
                continue
            try:
                ts = datetime.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if ts < cutoff:
                yyyy_mm = ts.strftime("%Y-%m")
                dest_dir = ARCHIVE_ENTRIES_DIR / yyyy_mm
                if not dry_run:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(f), str(dest_dir / f.name))
                else:
                    print(f"  [DRY RUN] Would archive: {f.name}")
                archived += 1

    return archived


def update_index(all_topics: dict[str, dict], dry_run: bool = False):
    """Regenerate _index.md and _tags.md."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Build tag index
    tag_to_topics: dict[str, list[str]] = defaultdict(list)
    for slug, info in all_topics.items():
        for tag in info.get("tags", []):
            tag_to_topics[tag].append(slug)

    # --- _index.md ---
    index_lines = [
        f"# Knowledge Graph Index\n",
        f"*Last updated: {today}*\n",
        f"\n{len(all_topics)} topic{'s' if len(all_topics) != 1 else ''} · "
        f"{len(tag_to_topics)} unique tag{'s' if len(tag_to_topics) != 1 else ''}\n",
        "\n## Topics\n",
    ]
    for slug in sorted(all_topics.keys()):
        info = all_topics[slug]
        name = info.get("topic", slug)
        updated = info.get("updated", today)
        tags = info.get("tags", [])
        tags_str = ", ".join(f"`{t}`" for t in tags[:5])
        n_findings = info.get("n_findings", 0)
        index_lines.append(
            f"- **[{name}](knowledge/{slug}.md)** — updated {updated}, "
            f"{n_findings} finding{'s' if n_findings != 1 else ''} · {tags_str}"
        )

    index_lines += [
        "\n## Tags\n",
        f"*See [_tags.md](knowledge/_tags.md) for full tag index.*\n",
        "\n## Navigation\n",
        "- Browse by topic above\n",
        "- Browse by tag in [_tags.md](knowledge/_tags.md)\n",
        "- Source files in [lessons/](lessons/), [memory/entries/](memory/entries/)\n",
        "- Long-term patterns in [MEMORY.md](MEMORY.md)\n",
    ]

    index_text = "\n".join(index_lines)

    # --- _tags.md ---
    tags_lines = [
        f"# Knowledge Tag Index\n",
        f"*Last updated: {today}*\n",
        f"\n{len(tag_to_topics)} unique tags across {len(all_topics)} topics\n",
        "\n## Tags → Topics\n",
    ]
    for tag in sorted(tag_to_topics.keys()):
        topic_slugs = sorted(tag_to_topics[tag])
        topic_links = ", ".join(
            f"[{all_topics.get(s, {}).get('topic', s)}](knowledge/{s}.md)"
            for s in topic_slugs
        )
        tags_lines.append(f"- **`{tag}`** → {topic_links}")

    tags_text = "\n".join(tags_lines)

    if dry_run:
        print(f"  [DRY RUN] Would update knowledge/_index.md ({len(all_topics)} topics)")
        print(f"  [DRY RUN] Would update knowledge/_tags.md ({len(tag_to_topics)} tags)")
        return

    KNOWLEDGE_DIR.mkdir(exist_ok=True)
    (KNOWLEDGE_DIR / "_index.md").write_text(index_text)
    (KNOWLEDGE_DIR / "_tags.md").write_text(tags_text)


def sync(week_start: datetime, dry_run: bool = False, all_agents: bool = False) -> dict:
    """Run the full weekly sync. Returns summary stats."""
    today = datetime.now(timezone.utc)
    week_end = week_start + timedelta(days=7)
    archival_cutoff = today - timedelta(days=7)

    print(f"\n🔄 Weekly Knowledge Sync")
    print(f"   Week: {week_start.strftime('%Y-%m-%d')} → {week_end.strftime('%Y-%m-%d')}")
    if all_agents:
        print("   Mode: All Agents")
    if dry_run:
        print("   Mode: DRY RUN\n")
    else:
        print()

    KNOWLEDGE_DIR.mkdir(exist_ok=True)

    # --- A. Load source material ---
    lessons = load_week_lessons(week_start)
    if all_agents:
        # Load entries from all agent workspaces (returns (path, fm, agent_name) tuples)
        memory_entries = load_all_agent_memory_entries(week_start)
    else:
        memory_entries = load_week_memory_entries(week_start)
    print(f"📚 Source material: {len(lessons)} lessons, {len(memory_entries)} memory entries")

    # --- B. Build topic data ---
    # topic_slug → {topic, tags, findings, sources, related, created}
    topic_data: dict[str, dict] = {}

    # Load existing knowledge files first
    if KNOWLEDGE_DIR.exists():
        for kf in KNOWLEDGE_DIR.glob("*.md"):
            if kf.stem.startswith("_"):
                continue
            fm, findings = load_knowledge_file(kf.stem)
            if fm:
                topic_data[kf.stem] = {
                    "topic": fm.get("topic", TOPIC_NAMES.get(kf.stem, kf.stem)),
                    "tags": fm.get("tags", []),
                    "findings": findings,
                    "sources": fm.get("sources", []),
                    "related": fm.get("related", []),
                    "created": fm.get("created", today.strftime("%Y-%m-%d")),
                    "updated": fm.get("updated", today.strftime("%Y-%m-%d")),
                    "n_findings": len(findings),
                }

    # Ensure standard topics exist
    for slug, name in TOPIC_NAMES.items():
        if slug not in topic_data:
            topic_data[slug] = {
                "topic": name,
                "tags": [t for t in TOPIC_KEYWORDS.get(slug, []) if len(t) > 3][:8],
                "findings": [],
                "sources": [],
                "related": [],
                "created": today.strftime("%Y-%m-%d"),
                "updated": today.strftime("%Y-%m-%d"),
                "n_findings": 0,
            }

    def integrate_text(text: str, source_ref: str, date_str: str):
        """Detect topics in text and add findings."""
        topics = detect_topics(text)
        for slug in topics:
            if slug not in topic_data:
                topic_data[slug] = {
                    "topic": TOPIC_NAMES.get(slug, slug.replace("-", " ").title()),
                    "tags": [t for t in TOPIC_KEYWORDS.get(slug, []) if len(t) > 3][:8],
                    "findings": [],
                    "sources": [],
                    "related": [],
                    "created": date_str,
                    "updated": today.strftime("%Y-%m-%d"),
                    "n_findings": 0,
                }
            td = topic_data[slug]
            # Extract bullet-worthy sentences (lines starting with - or key phrases)
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                # Lines that look like findings
                if (
                    line.startswith("-")
                    or line.startswith("•")
                    or len(line) > 20 and any(
                        kw in line.lower() for kw in [
                            "always", "never", "must", "should", "key", "important",
                            "found", "discovered", "pattern", "best", "avoid", "use",
                            "beats", "outperforms", "fails", "works", "causes",
                        ]
                    )
                ):
                    finding = f"- {line.lstrip('- •')} *({source_ref})*"
                    td["findings"].append(finding)
                    td["n_findings"] = len(td["findings"])

            if source_ref not in td["sources"]:
                td["sources"].append(source_ref)

    # Process lessons
    n_lessons_integrated = 0
    for path, fm, body in lessons:
        date_str = fm.get("date", today.strftime("%Y-%m-%d"))
        source_ref = str(path.relative_to(WORKSPACE))
        # Combine tags and body text for topic detection
        all_text = " ".join(fm.get("tags", [])) + " " + body
        integrate_text(all_text, source_ref, date_str)
        n_lessons_integrated += 1

    # Process memory entries
    n_memories_integrated = 0
    for entry in memory_entries:
        if len(entry) == 3:
            path, fm, agent_name = entry
        else:
            path, fm = entry
            agent_name = "main"
        ts = fm.get("timestamp", today.strftime("%Y-%m-%dT%H:%M:%SZ"))
        date_str = ts[:10]
        # Use relative path if possible, else abs
        try:
            source_ref = str(path.relative_to(WORKSPACE))
        except ValueError:
            source_ref = str(path)
        content = fm.get("content", "").replace('\\"', '"')
        tags_text = " ".join(fm.get("tags", []))
        all_text = content + " " + tags_text
        if fm.get("importance", "3") >= "3":  # Only high-value memories
            integrate_text(all_text, source_ref, date_str)
            n_memories_integrated += 1

    print(f"✓ Integrated {n_lessons_integrated} lessons, {n_memories_integrated} memory entries")

    # Build cross-references (topics that share sources or keywords)
    for slug_a in topic_data:
        for slug_b in topic_data:
            if slug_a >= slug_b:
                continue
            # Share keywords if they share >= 2 sources
            sources_a = set(topic_data[slug_a]["sources"])
            sources_b = set(topic_data[slug_b]["sources"])
            if len(sources_a & sources_b) >= 2:
                if slug_b not in topic_data[slug_a]["related"]:
                    topic_data[slug_a]["related"].append(slug_b)
                if slug_a not in topic_data[slug_b]["related"]:
                    topic_data[slug_b]["related"].append(slug_a)

    # --- C. Write knowledge files ---
    n_files_written = 0
    for slug, td in topic_data.items():
        if not td["findings"] and not td["sources"]:
            continue  # Don't create empty files for unused topics
        write_knowledge_file(
            slug=slug,
            topic_name=td["topic"],
            tags=td["tags"],
            findings=td["findings"],
            sources=td["sources"],
            related=td["related"],
            created=td["created"],
            dry_run=dry_run,
        )
        n_files_written += 1

    print(f"✓ Wrote {n_files_written} knowledge files")

    # Update index
    update_index(topic_data, dry_run=dry_run)
    print(f"✓ Updated knowledge/_index.md and knowledge/_tags.md")

    # --- D. Archive old files ---
    print(f"\n📦 Archiving files older than {archival_cutoff.strftime('%Y-%m-%d')}...")
    n_archived = archive_old_files(archival_cutoff, dry_run=dry_run)
    print(f"✓ Archived {n_archived} file{'s' if n_archived != 1 else ''}")

    # --- E. Cross-agent synthesis (when --all-agents) ---
    if all_agents:
        print(f"\n🧬 Generating cross-agent synthesis section...")
        # all_entries has (path, fm, agent_name) tuples
        synthesis = generate_cross_agent_synthesis(memory_entries, week_start, dry_run=dry_run)
        # Append synthesis to main weekly knowledge index
        weekly_synthesis_file = KNOWLEDGE_DIR / "_weekly_synthesis.md"
        if dry_run:
            print(f"  [DRY RUN] Would write cross-agent synthesis to knowledge/_weekly_synthesis.md")
            print(synthesis)
        else:
            # Append / overwrite with latest synthesis
            existing = weekly_synthesis_file.read_text() if weekly_synthesis_file.exists() else ""
            # Prepend new synthesis (most recent first)
            weekly_synthesis_file.write_text(synthesis + "\n---\n" + existing)
            print(f"  ✓ Cross-agent synthesis written to knowledge/_weekly_synthesis.md")

    stats = {
        "lessons": n_lessons_integrated,
        "memories": n_memories_integrated,
        "knowledge_files": n_files_written,
        "archived": n_archived,
        "dry_run": dry_run,
        "all_agents": all_agents,
    }

    print(f"\n{'[DRY RUN] ' if dry_run else ''}✅ Weekly sync complete:")
    print(f"   {n_lessons_integrated} lessons + {n_memories_integrated} memories → {n_files_written} knowledge files")
    print(f"   {n_archived} files archived")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Weekly knowledge graph sync — processes lessons and memory entries.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/weekly_knowledge_sync.py
  python3 scripts/weekly_knowledge_sync.py --week 2026-03-10
  python3 scripts/weekly_knowledge_sync.py --dry-run
  python3 scripts/weekly_knowledge_sync.py --all-agents
  python3 scripts/weekly_knowledge_sync.py --all-agents --dry-run
        """,
    )
    parser.add_argument(
        "--week",
        help="Week start date (YYYY-MM-DD, default: 7 days ago)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would happen without writing files",
    )
    parser.add_argument(
        "--all-agents",
        action="store_true",
        help="Read memory entries from ALL agent workspaces (main + architect + critic + builder)",
    )

    args = parser.parse_args()

    if args.week:
        try:
            week_start = datetime.strptime(args.week, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"Error: Invalid date format '{args.week}'. Use YYYY-MM-DD.")
            sys.exit(1)
    else:
        # Default: last 7 days
        week_start = datetime.now(timezone.utc) - timedelta(days=7)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    sync(week_start, dry_run=args.dry_run, all_agents=args.all_agents)


if __name__ == "__main__":
    main()
