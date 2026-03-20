---
primitive: lesson
date: 2026-03-18
source: "Agent infrastructure redesign session with Shael"
confidence: high
project: snn-applied-finance
tags: [infrastructure, agents, orchestration, pattern]
applies_to: [orchestrator, pipeline-autorun, agent-management]
upstream: [decision/agent-session-isolation, decision/orchestration-architecture]
---

# Lesson: Checkpoint-and-Resume for Long Agent Tasks

## Pattern
When an agent times out mid-work (10 min limit), don't retry blindly — checkpoint what was done, then resume with context.

## Implementation
1. **On timeout:** Scan `pipeline_builds/` for files modified in last 12 min
2. **Write checkpoint:** Agent's `memory/YYYY-MM-DD.md` gets timestamped entry with partial file list
3. **Fresh session:** Generate new UUID4, reset agent sessions (main + group)
4. **Resume message:** Tells agent to read memory checkpoint first, check for partial work, continue — not restart
5. **Limit:** 5 resume cycles (60 min total) before alerting human

## Why It Works
- Agent memory files survive session resets (they're on disk, not in session context)
- Partial artifacts (design docs, notebooks) also survive on shared filesystem
- Each resume builds on accumulated checkpoints — the agent gets smarter about what's left to do

## Three-Tier Recovery Chain
This pattern is tier 2 of 3. Full chain:
1. **Stale lock detection (5 min)** — `pipeline_autorun.py --check-locks` kills hung PIDs, clears lock files
2. **Checkpoint-and-resume (10 min)** — this pattern, saves partial work and re-wakes with context
3. **Pipeline stall recovery (120 min)** — `pipeline_autorun.py --check-stalled` full re-kick

## Anti-Pattern
Don't use deterministic session IDs (UUID5) hoping to "continue" a session — OpenClaw sessions accumulate context, leading to confusion. Always use fresh UUID4 + memory files for continuity.
