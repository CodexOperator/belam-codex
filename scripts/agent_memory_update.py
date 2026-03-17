#!/usr/bin/env python3
"""
agent_memory_update.py — Per-session memory capture for agents.

Called by pipeline_update.py after stage transitions, or by agents manually.

Usage:
  python3 scripts/agent_memory_update.py --agent architect --summary "Designed v4-deep methodology"
  python3 scripts/agent_memory_update.py --agent builder --pipeline v4-deep --stage builder_implementation \\
      --summary "Implemented 3 SNN layers with membrane readout"
  python3 scripts/agent_memory_update.py --agent critic --pipeline v4 --stage critic_code_review \\
      --summary "Approved implementation with 2 minor flags"
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

AGENT_WORKSPACES = {
    "main":      Path(os.path.expanduser("~/.openclaw/workspace")),
    "architect": Path(os.path.expanduser("~/.openclaw/workspace-architect")),
    "critic":    Path(os.path.expanduser("~/.openclaw/workspace-critic")),
    "builder":   Path(os.path.expanduser("~/.openclaw/workspace-builder")),
}

SCRIPTS_DIR = Path(__file__).parent


def build_memory_content(
    agent: str,
    pipeline: str | None,
    stage: str | None,
    summary: str,
) -> str:
    """Build the memory content string, enriched with pipeline/stage context."""
    parts = [summary]
    if pipeline and stage:
        parts.append(f"Pipeline: {pipeline} | Stage: {stage}")
    elif pipeline:
        parts.append(f"Pipeline: {pipeline}")
    elif stage:
        parts.append(f"Stage: {stage}")
    return " | ".join(parts)


def build_tags(agent: str, pipeline: str | None, stage: str | None) -> list[str]:
    """Build tags list from context."""
    tags = [f"agent:{agent}"]
    if pipeline:
        tags.append(f"pipeline:{pipeline}")
    if stage:
        tags.append(f"stage:{stage}")
    return tags


def auto_detect_importance(summary: str, stage: str | None) -> int:
    """Heuristic: stage completions are importance 3; blocks/failures are 4; design decisions are 4."""
    s = (summary + " " + (stage or "")).lower()
    if any(kw in s for kw in ["block", "fail", "error", "critical", "urgent", "broke"]):
        return 4
    if any(kw in s for kw in ["design", "decided", "approved", "complete", "phase"]):
        return 4
    if any(kw in s for kw in ["start", "begin", "implement", "build"]):
        return 3
    return 3


def log_memory_for_agent(
    agent: str,
    summary: str,
    pipeline: str | None = None,
    stage: str | None = None,
    category: str | None = None,
    importance: int | None = None,
) -> int:
    """Call log_memory.py for the agent's workspace. Returns subprocess returncode."""
    workspace = AGENT_WORKSPACES.get(agent)
    if not workspace:
        print(f"Error: Unknown agent '{agent}'. Valid agents: {list(AGENT_WORKSPACES.keys())}")
        return 1

    content = build_memory_content(agent, pipeline, stage, summary)
    tags = build_tags(agent, pipeline, stage)
    imp = importance or auto_detect_importance(summary, stage)
    source = f"pipeline_update:{pipeline}:{stage}" if pipeline and stage else f"agent_session:{agent}"

    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "log_memory.py"),
        "--workspace", str(workspace),
        "--importance", str(imp),
        "--tags", ",".join(tags),
        "--source", source,
        content,
    ]
    if category:
        cmd += ["--category", category]

    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Log a memory entry to a specific agent's workspace.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/agent_memory_update.py --agent architect --summary "Designed v4-deep methodology"
  python3 scripts/agent_memory_update.py --agent builder --pipeline v4-deep --stage builder_implementation \\
      --summary "Implemented 3 SNN layers with membrane potential readout"
  python3 scripts/agent_memory_update.py --agent critic --pipeline v4 --stage critic_code_review \\
      --summary "BLOCK: loss function incorrect, fix before proceeding"
        """,
    )
    parser.add_argument(
        "--agent", "-a",
        required=True,
        choices=list(AGENT_WORKSPACES.keys()),
        help="Agent to log memory for (architect|critic|builder|main)",
    )
    parser.add_argument(
        "--pipeline", "-p",
        help="Pipeline version (optional, e.g. v4-deep)",
    )
    parser.add_argument(
        "--stage", "-g",
        help="Pipeline stage just completed (optional)",
    )
    parser.add_argument(
        "--summary", "-s",
        required=True,
        help="What happened / what was learned",
    )
    parser.add_argument(
        "--category", "-c",
        choices=["insight", "decision", "preference", "context", "event", "technical", "relationship"],
        help="Memory category (auto-detected if omitted)",
    )
    parser.add_argument(
        "--importance", "-i",
        type=int,
        choices=range(1, 6),
        metavar="1-5",
        help="Importance 1-5 (auto-detected if omitted)",
    )

    args = parser.parse_args()

    rc = log_memory_for_agent(
        agent=args.agent,
        summary=args.summary,
        pipeline=args.pipeline,
        stage=args.stage,
        category=args.category,
        importance=args.importance,
    )
    sys.exit(rc)


if __name__ == "__main__":
    main()
