#!/usr/bin/env python3
"""
memory_daily_linker.py — Daily cross-referencing across wiki, transcripts, and recent memories.

Handles ALL daily cross-referencing:
  a) Wiki linking: topics in today's memory → knowledge/ wiki pages (bidirectional)
  b) Transcript linking: today's memory → relevant transcripts in conversations/
  c) Recent memory linking: today's memory ↔ past 3 days (see-also links)

Runs: as part of daily cron, AFTER consolidation.

Usage:
  python3 scripts/memory_daily_linker.py              # Link today's memory
  python3 scripts/memory_daily_linker.py --date 2026-03-17
  python3 scripts/memory_daily_linker.py --dry-run    # Preview only
"""

import argparse
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
MEMORY_DIR = WORKSPACE / "memory"
KNOWLEDGE_DIR = WORKSPACE / "knowledge"
CONVERSATIONS_BASE = WORKSPACE / "machinelearning" / "snn_applied_finance" / "conversations"

# Topic keywords for wiki detection
TOPIC_KEYWORDS = {
    "snn-architecture": [
        "snn", "spiking neural", "neuron", "leaky", "synaptic", "spike", "membrane",
        "snntorch", "lif", "refractory", "threshold", "integrate-and-fire",
    ],
    "financial-encoding": [
        "delta encoding", "rate coding", "population coding", "financial", "btc", "bitcoin",
        "candle", "ohlcv", "macd", "rsi", "orderbook", "trading", "prediction market",
    ],
    "gpu-optimization": [
        "gpu", "cuda", "tpu", "a100", "t4", "colab", "batch size", "mixed precision",
        "fp16", "throughput", "memory bandwidth", "tensor core",
    ],
    "agent-coordination": [
        "agent", "subagent", "sub-agent", "orchestrat", "coordinator", "heartbeat",
        "openclaw", "cron", "telegram", "sessions_send", "multi-agent",
    ],
    "experiment-methodology": [
        "experiment", "hypothesis", "accuracy", "loss", "metric", "sharpe",
        "backtest", "validation", "overfitting", "pipeline", "notebook",
        "v1", "v2", "v3", "v4", "v5",
    ],
    "ml-architecture": [
        "lstm", "transformer", "attention", "neural network", "deep learning",
        "gradient", "backprop", "optimizer", "adam", "learning rate",
        "dropout", "batch norm", "residual",
    ],
    "research-workflow": [
        "lesson", "insight", "decision", "knowledge", "memory", "consolidat",
        "workflow", "methodology", "commit", "git",
    ],
}

TOPIC_NAMES = {
    "snn-architecture": "SNN Architecture",
    "financial-encoding": "Financial Encoding",
    "gpu-optimization": "GPU Optimization",
    "agent-coordination": "Agent Coordination",
    "experiment-methodology": "Experiment Methodology",
    "ml-architecture": "ML Architecture",
    "research-workflow": "Research Workflow",
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def detect_topics(text: str) -> list[str]:
    """Return list of topic slugs found in text."""
    text_lower = text.lower()
    matched = []
    for topic_slug, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                matched.append(topic_slug)
                break
    return matched


def link_already_exists(content: str, link_url: str) -> bool:
    """Check if a link URL already appears in the content."""
    return link_url in content


def append_see_also(filepath: Path, links: list[str], dry_run: bool = False) -> bool:
    """
    Append links to a See Also section in a file.
    Creates the section if it doesn't exist.
    Returns True if any changes were made.
    """
    if not filepath.exists():
        return False

    content = filepath.read_text()
    new_links = []

    for link in links:
        url_match = re.search(r"\(([^)]+)\)", link)
        if url_match:
            url = url_match.group(1)
            if link_already_exists(content, url):
                continue
        new_links.append(link)

    if not new_links:
        return False

    if dry_run:
        print(f"  [DRY RUN] Would add to {filepath.name}:")
        for link in new_links:
            print(f"    {link}")
        return True

    if "## See Also" in content:
        content = content.rstrip() + "\n" + "\n".join(new_links) + "\n"
    else:
        content = content.rstrip() + "\n\n## See Also\n\n" + "\n".join(new_links) + "\n"

    filepath.write_text(content)
    return True


# ─── a) Wiki linking ──────────────────────────────────────────────────────────

def link_daily_to_wiki(daily_file: Path, date_str: str, dry_run: bool = False) -> int:
    """
    Scan daily memory for topic matches. Add links daily→wiki and wiki→daily.
    Returns number of wiki pages linked.
    """
    if not daily_file.exists():
        print(f"  Daily file not found: {daily_file.name}")
        return 0

    content = daily_file.read_text()
    topics = detect_topics(content)

    if not topics:
        print(f"  No wiki topics detected in {daily_file.name}")
        return 0

    linked = 0
    for topic_slug in topics:
        wiki_file = KNOWLEDGE_DIR / f"{topic_slug}.md"
        if not wiki_file.exists():
            print(f"  Wiki page not found: {topic_slug}.md (skipping)")
            continue

        topic_name = TOPIC_NAMES.get(topic_slug, topic_slug.replace("-", " ").title())

        # daily → wiki link
        wiki_rel = f"../knowledge/{topic_slug}.md"
        daily_link = f"- [→ Wiki: {topic_name}]({wiki_rel})"
        append_see_also(daily_file, [daily_link], dry_run=dry_run)

        # wiki → daily link
        daily_rel = f"../memory/{date_str}.md"
        wiki_link = f"- [→ Daily {date_str}]({daily_rel})"
        append_see_also(wiki_file, [wiki_link], dry_run=dry_run)

        linked += 1
        if not dry_run:
            print(f"  ↔ Linked {daily_file.name} ↔ knowledge/{topic_slug}.md")

    return linked


# ─── b) Transcript linking ────────────────────────────────────────────────────

def find_recent_transcripts(days_back: int = 3) -> list[Path]:
    """Find transcript files modified in the last N days."""
    if not CONVERSATIONS_BASE.exists():
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    transcripts = []

    for f in sorted(CONVERSATIONS_BASE.rglob("*.md")):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime >= cutoff:
                transcripts.append(f)
        except OSError:
            continue

    return transcripts


def topic_overlap(text_a: str, text_b: str) -> list[str]:
    """Return topic slugs that appear in both texts."""
    topics_a = set(detect_topics(text_a))
    topics_b = set(detect_topics(text_b))
    return list(topics_a & topics_b)


def link_daily_to_transcripts(daily_file: Path, date_str: str, dry_run: bool = False) -> int:
    """
    Find recent transcripts with overlapping topics and cross-link.
    Returns number of transcripts linked.
    """
    if not daily_file.exists():
        return 0

    daily_content = daily_file.read_text()
    transcripts = find_recent_transcripts(days_back=3)

    if not transcripts:
        print(f"  No recent transcripts found in {CONVERSATIONS_BASE}")
        return 0

    linked = 0
    for transcript in transcripts:
        try:
            transcript_content = transcript.read_text()
        except OSError:
            continue

        shared_topics = topic_overlap(daily_content, transcript_content)
        if not shared_topics:
            continue

        topic_names = [TOPIC_NAMES.get(t, t) for t in shared_topics[:3]]
        topics_str = ", ".join(topic_names)

        # Compute relative paths
        try:
            transcript_rel = f"../{transcript.relative_to(WORKSPACE)}"
        except ValueError:
            transcript_rel = str(transcript)

        try:
            daily_rel = f"../../../memory/{date_str}.md"
        except Exception:
            daily_rel = f"../memory/{date_str}.md"

        # daily → transcript
        daily_link = f"- [→ Transcript: {transcript.name}]({transcript_rel}) *({topics_str})*"
        append_see_also(daily_file, [daily_link], dry_run=dry_run)

        # transcript → daily
        transcript_link = f"- [→ Daily Memory {date_str}]({daily_rel}) *({topics_str})*"
        append_see_also(transcript, [transcript_link], dry_run=dry_run)

        linked += 1
        if not dry_run:
            print(f"  ↔ Linked {daily_file.name} ↔ {transcript.name} (topics: {topics_str})")

    return linked


# ─── c) Recent memory linking ─────────────────────────────────────────────────

def link_recent_memories(daily_file: Path, date_str: str, days_back: int = 3,
                          dry_run: bool = False) -> int:
    """
    Cross-reference today's memory with the past N days.
    Add see-also links where topics overlap.
    Returns number of cross-links added.
    """
    if not daily_file.exists():
        return 0

    today_content = daily_file.read_text()
    today_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    today_topics = set(detect_topics(today_content))

    if not today_topics:
        print(f"  No topics in {daily_file.name}, skipping recent memory links")
        return 0

    linked = 0
    for i in range(1, days_back + 1):
        past_date = today_date - timedelta(days=i)
        past_date_str = past_date.strftime("%Y-%m-%d")
        past_file = MEMORY_DIR / f"{past_date_str}.md"

        if not past_file.exists():
            continue

        past_content = past_file.read_text()
        shared_topics = set(detect_topics(past_content)) & today_topics

        if not shared_topics:
            continue

        topic_names = [TOPIC_NAMES.get(t, t) for t in list(shared_topics)[:3]]
        topics_str = ", ".join(topic_names)

        # today → past
        today_to_past = f"- [→ See also: {past_date_str}]({past_date_str}.md) *({topics_str})*"
        append_see_also(daily_file, [today_to_past], dry_run=dry_run)

        # past → today
        past_to_today = f"- [→ See also: {date_str}]({date_str}.md) *({topics_str})*"
        append_see_also(past_file, [past_to_today], dry_run=dry_run)

        linked += 1
        if not dry_run:
            print(f"  ↔ Cross-linked {date_str} ↔ {past_date_str} (topics: {topics_str})")

    return linked


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Daily cross-referencing: wiki, transcripts, and recent memory links.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/memory_daily_linker.py
  python3 scripts/memory_daily_linker.py --date 2026-03-17
  python3 scripts/memory_daily_linker.py --dry-run
        """,
    )
    parser.add_argument("--date", help="Date to process (YYYY-MM-DD). Default: today UTC.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes.")
    args = parser.parse_args()

    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily_file = MEMORY_DIR / f"{date_str}.md"

    print(f"🔗 Memory Daily Linker — {date_str}")
    if args.dry_run:
        print("   Mode: DRY RUN\n")

    if not daily_file.exists():
        print(f"⚠️  Daily file not found: {daily_file}")
        print("   Run consolidate_memories.py first.")
        return

    # ── a) Wiki linking ───────────────────────────────────────────────────────
    print(f"\n🌐 a) Wiki linking")
    n_wiki = link_daily_to_wiki(daily_file, date_str, dry_run=args.dry_run)
    print(f"   Linked to {n_wiki} wiki page(s)")

    # ── b) Transcript linking ─────────────────────────────────────────────────
    print(f"\n📝 b) Transcript linking")
    n_transcripts = link_daily_to_transcripts(daily_file, date_str, dry_run=args.dry_run)
    print(f"   Linked to {n_transcripts} transcript(s)")

    # ── c) Recent memory linking ──────────────────────────────────────────────
    print(f"\n📅 c) Recent memory cross-linking (past 3 days)")
    n_recent = link_recent_memories(daily_file, date_str, days_back=3, dry_run=args.dry_run)
    print(f"   Cross-linked with {n_recent} recent daily file(s)")

    total = n_wiki + n_transcripts + n_recent
    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}✅ Daily linking complete — {total} links added")


if __name__ == "__main__":
    main()
