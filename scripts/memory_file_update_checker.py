#!/usr/bin/env python3
"""
memory_file_update_checker.py — Post-consolidation file update checker.

Checks whether today's memory modifications require updates to other workspace files.
Scans tasks, decisions, lessons, projects, and agent files for stale references.
Makes low-risk changes directly; reports high-risk ones.

Runs: as part of daily cron, AFTER linker.

Usage:
  python3 scripts/memory_file_update_checker.py              # Check today
  python3 scripts/memory_file_update_checker.py --date 2026-03-17
  python3 scripts/memory_file_update_checker.py --dry-run    # Preview only
"""

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
MEMORY_DIR = WORKSPACE / "memory"
TASKS_DIR = WORKSPACE / "tasks"
LESSONS_DIR = WORKSPACE / "lessons"
DECISIONS_DIR = WORKSPACE / "decisions"
PROJECTS_DIR = WORKSPACE / "projects"
SCRIPTS_DIR = WORKSPACE / "scripts"
REPORT_FILE = MEMORY_DIR / "daily_update_report.md"

AGENT_FILES = [
    WORKSPACE / "SOUL.md",
    WORKSPACE / "IDENTITY.md",
    WORKSPACE / "AGENTS.md",
    WORKSPACE / "AGENT_SOUL.md",
    WORKSPACE / "MEMORY.md",
    WORKSPACE / "TOOLS.md",
]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def read_frontmatter(filepath: Path) -> dict:
    """Parse YAML frontmatter from a markdown file."""
    if not filepath.exists():
        return {}
    text = filepath.read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"').strip("'")
    # Parse list fields
    for key in ("tags", "depends_on"):
        if key in fm:
            raw = fm[key].strip("[]")
            fm[key] = [t.strip().strip('"').strip("'") for t in raw.split(",") if t.strip()]
        else:
            fm[key] = []
    return fm


def update_frontmatter_field(filepath: Path, field: str, new_value: str) -> bool:
    """Update a single frontmatter field. Returns True if changed."""
    if not filepath.exists():
        return False
    text = filepath.read_text()
    pattern = rf"^{re.escape(field)}:.*$"
    updated = re.sub(pattern, f"{field}: {new_value}", text, flags=re.MULTILINE)
    if updated != text:
        filepath.write_text(updated)
        return True
    return False


def extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from text (slugifiable words 4+ chars)."""
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9-]{3,}\b", text.lower())
    return set(words)


# ─── a) Scan workspace modifications ─────────────────────────────────────────

def get_daily_memory_content(date_str: str) -> str:
    """Read today's daily memory file."""
    daily_file = MEMORY_DIR / f"{date_str}.md"
    if daily_file.exists():
        return daily_file.read_text()
    return ""


# ─── b) Check tasks for status updates ───────────────────────────────────────

def check_tasks(memory_content: str) -> list[dict]:
    """
    Check if any task status updates are implied by memory content.
    Returns list of {file, field, old_value, new_value, reason, risk}.
    """
    changes = []
    if not TASKS_DIR.exists():
        return changes

    memory_lower = memory_content.lower()

    for task_file in sorted(TASKS_DIR.glob("*.md")):
        fm = read_frontmatter(task_file)
        current_status = fm.get("status", "open")
        task_slug = task_file.stem
        task_words = set(task_slug.replace("-", " ").split() + task_slug.split("-"))

        # Skip already completed/archived
        if current_status in ("complete", "archived", "done"):
            continue

        # Check if memory mentions completion of this task
        completion_signals = [
            f"completed {task_slug}",
            f"finished {task_slug}",
            f"{task_slug} complete",
            f"{task_slug} done",
            f"deployed {task_slug}",
        ]
        # Also check by task words
        task_mentioned = any(word in memory_lower for word in task_words if len(word) > 4)

        completed_mentioned = any(sig in memory_lower for sig in completion_signals)

        if completed_mentioned:
            changes.append({
                "file": task_file,
                "field": "status",
                "old_value": current_status,
                "new_value": "complete",
                "reason": f"Memory mentions completion of {task_slug}",
                "risk": "low",
            })
        elif task_mentioned and "blocked" in memory_lower:
            # Check if task is blocked
            if current_status not in ("blocked",):
                changes.append({
                    "file": task_file,
                    "field": "status",
                    "old_value": current_status,
                    "new_value": "blocked",
                    "reason": f"Memory mentions {task_slug} is blocked",
                    "risk": "low",
                })

    return changes


# ─── c) Check decisions for superseded ones ───────────────────────────────────

def check_decisions(memory_content: str) -> list[dict]:
    """
    Check if any decisions have been superseded by content in today's memory.
    Returns list of change recommendations.
    """
    changes = []
    if not DECISIONS_DIR.exists():
        return changes

    memory_lower = memory_content.lower()

    for decision_file in sorted(DECISIONS_DIR.glob("*.md")):
        fm = read_frontmatter(decision_file)
        current_status = fm.get("status", "active")
        decision_slug = decision_file.stem

        if current_status in ("superseded", "archived"):
            continue

        # Check if memory mentions superseding this decision
        supersede_signals = [
            f"supersedes {decision_slug}",
            f"replaces {decision_slug}",
            f"overrides {decision_slug}",
            f"instead of {decision_slug}",
        ]

        if any(sig in memory_lower for sig in supersede_signals):
            changes.append({
                "file": decision_file,
                "field": "status",
                "old_value": current_status,
                "new_value": "superseded",
                "reason": f"Memory mentions superseding decision {decision_slug}",
                "risk": "low",
            })

    return changes


# ─── d) Check agent files for stale references ────────────────────────────────

def check_agent_files(memory_content: str) -> list[dict]:
    """
    Check if agent files (SOUL.md, IDENTITY.md, etc.) reference anything that's changed.
    Returns high-risk recommendations.
    """
    changes = []
    # Only flag agent files if memory explicitly mentions changes TO those files
    # or describes role/identity/workflow changes that should be reflected
    change_signals = {
        "SOUL.md": ["soul updated", "soul change", "update soul", "changed soul", "new soul"],
        "IDENTITY.md": ["identity change", "role change", "new role", "renamed to", "identity updated"],
        "AGENTS.md": ["agents updated", "workflow change", "new convention", "agents.md change"],
        "MEMORY.md": ["memory structure change", "memory format", "update memory.md"],
        "TOOLS.md": ["new tool", "tool change", "tools updated", "tool removed"],
    }

    memory_lower = memory_content.lower()
    for agent_file in AGENT_FILES:
        if not agent_file.exists():
            continue

        signals = change_signals.get(agent_file.name, [])
        triggered = [s for s in signals if s in memory_lower]

        if triggered:
            changes.append({
                "file": agent_file,
                "field": "content",
                "old_value": f"current ({len(agent_file.read_text())} chars)",
                "new_value": f"change signal detected: {', '.join(triggered)}",
                "reason": f"Memory mentions changes relevant to {agent_file.name}: {', '.join(triggered)}",
                "risk": "high",
            })

    return changes


# ─── e) Check scripts for relevant changes ────────────────────────────────────

def check_scripts(memory_content: str) -> list[dict]:
    """
    Check if any scripts need modification based on patterns/tool changes in memory.
    Returns high-risk recommendations only.
    """
    changes = []
    memory_lower = memory_content.lower()

    # Look for script change signals
    script_signals = [
        ("cron", "setup_memory_crons.py", "Cron schedule change mentioned"),
        ("api change", None, "API change detected — scripts may need updates"),
        ("deprecated", None, "Deprecation mentioned — check script compatibility"),
        ("new tool", None, "New tool mentioned — scripts may need integration"),
        ("broke", None, "Script break mentioned — review scripts"),
        ("bug in", None, "Bug mentioned — review affected scripts"),
    ]

    for signal, target_script, reason in script_signals:
        if signal in memory_lower:
            if target_script:
                script_file = SCRIPTS_DIR / target_script
                if script_file.exists():
                    changes.append({
                        "file": script_file,
                        "field": "content",
                        "old_value": "current",
                        "new_value": "may need update",
                        "reason": reason,
                        "risk": "high",
                    })
            else:
                changes.append({
                    "file": SCRIPTS_DIR,
                    "field": "directory",
                    "old_value": "current",
                    "new_value": "may need updates",
                    "reason": reason,
                    "risk": "high",
                })

    return changes


# ─── Apply low-risk changes ───────────────────────────────────────────────────

def apply_low_risk_change(change: dict, dry_run: bool = False) -> bool:
    """Apply a low-risk change (status update, link addition). Returns True if applied."""
    filepath = change["file"]
    field = change["field"]
    new_value = change["new_value"]

    if dry_run:
        print(f"  [DRY RUN] Would update {filepath.name}: {field} → {new_value}")
        return True

    if field == "status":
        result = update_frontmatter_field(filepath, "status", new_value)
        if result:
            print(f"  ✓ Updated {filepath.name}: status → {new_value}")
        return result

    return False


# ─── Report generation ────────────────────────────────────────────────────────

def generate_report(date_str: str, all_changes: list[dict],
                     applied_count: int, dry_run: bool = False) -> str:
    """Generate the daily update report."""
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    low_risk = [c for c in all_changes if c.get("risk") == "low"]
    high_risk = [c for c in all_changes if c.get("risk") == "high"]

    lines = [
        f"# Daily Update Report — {date_str}",
        f"",
        f"*Generated: {now_ts}*  ",
        f"*Total recommendations: {len(all_changes)} ({len(low_risk)} low-risk, {len(high_risk)} high-risk)*  ",
        f"*Applied: {applied_count} changes*",
        f"",
    ]

    if not all_changes:
        lines.append("✅ No updates needed — workspace is current.")
        lines.append("")
    else:
        if low_risk:
            lines.append("## ✅ Low-Risk Changes (Applied)")
            lines.append("")
            for c in low_risk:
                filepath = c["file"]
                try:
                    rel = filepath.relative_to(WORKSPACE)
                except ValueError:
                    rel = filepath
                lines.append(f"- **{rel}**: `{c['field']}` → `{c['new_value']}`")
                lines.append(f"  *Reason: {c['reason']}*")
            lines.append("")

        if high_risk:
            lines.append("## ⚠️ High-Risk Changes (Review Required)")
            lines.append("")
            lines.append("*These changes were NOT applied automatically. Review and apply manually.*")
            lines.append("")
            for c in high_risk:
                filepath = c["file"]
                try:
                    rel = filepath.relative_to(WORKSPACE)
                except ValueError:
                    rel = filepath
                lines.append(f"- **{rel}**: {c['reason']}")
                lines.append(f"  *Current: {c['old_value']} → Suggested: {c['new_value']}*")
            lines.append("")

    lines.append("---")
    lines.append(f"*Report for: memory/{date_str}.md*")
    lines.append("")

    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Post-consolidation file update checker.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/memory_file_update_checker.py
  python3 scripts/memory_file_update_checker.py --date 2026-03-17
  python3 scripts/memory_file_update_checker.py --dry-run
        """,
    )
    parser.add_argument("--date", help="Date to check (YYYY-MM-DD). Default: today UTC.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes.")
    args = parser.parse_args()

    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"🔍 Memory File Update Checker — {date_str}")
    if args.dry_run:
        print("   Mode: DRY RUN\n")

    # Load today's memory content
    memory_content = get_daily_memory_content(date_str)
    if not memory_content:
        print(f"⚠️  No memory content found for {date_str}")
        print("   Run consolidate_memories.py first.")
        # Still generate an empty report
        report = generate_report(date_str, [], 0, dry_run=args.dry_run)
        if not args.dry_run:
            REPORT_FILE.write_text(report)
            print(f"✓ Empty report written: {REPORT_FILE.relative_to(WORKSPACE)}")
        return

    all_changes = []
    applied_count = 0

    # ── b) Check tasks ────────────────────────────────────────────────────────
    print(f"\n📋 b) Checking tasks for status updates")
    task_changes = check_tasks(memory_content)
    all_changes.extend(task_changes)
    print(f"   {len(task_changes)} task change(s) identified")

    # ── c) Check decisions ────────────────────────────────────────────────────
    print(f"\n⚖️  c) Checking decisions for superseded status")
    decision_changes = check_decisions(memory_content)
    all_changes.extend(decision_changes)
    print(f"   {len(decision_changes)} decision change(s) identified")

    # ── d) Check agent files ──────────────────────────────────────────────────
    print(f"\n🤖 d) Checking agent files for stale references")
    agent_changes = check_agent_files(memory_content)
    all_changes.extend(agent_changes)
    print(f"   {len(agent_changes)} agent file issue(s) identified")

    # ── e) Check scripts ──────────────────────────────────────────────────────
    print(f"\n📜 e) Checking scripts for required updates")
    script_changes = check_scripts(memory_content)
    all_changes.extend(script_changes)
    print(f"   {len(script_changes)} script issue(s) identified")

    # ── f) Apply low-risk changes ─────────────────────────────────────────────
    print(f"\n✅ f) Applying low-risk changes")
    low_risk = [c for c in all_changes if c.get("risk") == "low"]
    for change in low_risk:
        if apply_low_risk_change(change, dry_run=args.dry_run):
            applied_count += 1

    if not low_risk:
        print(f"   No low-risk changes to apply")

    # ── g) Generate report ────────────────────────────────────────────────────
    print(f"\n📄 g) Generating update report")
    report = generate_report(date_str, all_changes, applied_count, dry_run=args.dry_run)

    if args.dry_run:
        print("\n[DRY RUN] Would write report:")
        print("─" * 60)
        print(report)
        print("─" * 60)
    else:
        REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        REPORT_FILE.write_text(report)
        print(f"   ✓ Report written: {REPORT_FILE.relative_to(WORKSPACE)}")

    total = len(all_changes)
    high_count = len([c for c in all_changes if c.get("risk") == "high"])

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}✅ File update check complete — "
          f"{total} recommendation(s), {applied_count} applied, {high_count} need review")


if __name__ == "__main__":
    main()
