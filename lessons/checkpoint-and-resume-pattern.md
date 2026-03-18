---
primitive: lesson
date: 2026-03-18
source: "Agent infrastructure redesign session with Shael"
confidence: high
project: snn-applied-finance
tags: [infrastructure, agents, orchestration, pattern]
applies_to: [orchestrator, pipeline-autorun, agent-management]
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

## Anti-Pattern
Don't use deterministic session IDs (UUID5) hoping to "continue" a session — OpenClaw sessions accumulate context, leading to confusion. Always use fresh UUID4 + memory files for continuity.
