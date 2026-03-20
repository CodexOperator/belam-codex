---
primitive: decision
date: 2026-03-20
status: accepted
upstream: []
downstream: []
tags: [instance:main, memory-extraction, automation, architecture, bootstrap-hook]
---

# auto-memory-extraction-architecture

## Decision

Implement automated session memory extraction as a hook → marker → subagent pipeline rather than direct hook spawning or manual orchestration.

## Context

Shael asked for automated extraction of memories/lessons/decisions from every session when `/new` or `/reset` is called — replacing manual memory consolidation and making the system independent of reminder or manual use.

## Options Considered

1. **Direct spawn from hook handler** — rejected: the hook fires while the session lock is held; any attempt to run `openclaw agent --agent main` collides with the active lock
2. **Separate agent (code-tutor etc.)** — possible but awkward; the extraction agent should have main workspace access
3. **Hook writes marker → agent spawns on boot** — accepted: clean separation, uses `sessions_spawn` from within the active session, no lock collision
4. **Orchestrator script only** — already existed partially; too manual, too dependent on external triggering

## Rationale

The marker-file approach decouples the lock window from the extraction trigger. The agent (main) reads `memory/pending_extraction.json` on startup as part of its AGENTS.md startup sequence, spawns the extraction subagent via `sessions_spawn`, and the subagent runs fire-and-forget with push-based completion announcements.

## Components Built

- `hooks/memory-extract/handler.ts` — writes marker file on `agent:bootstrap`, includes prev session path + instance + persona
- `scripts/extract_session_memory.sh` — orchestrates: find JSONL, call parser, build prompt, spawn subagent
- `scripts/parse_session_transcript.py` — converts JSONL → condensed markdown transcript (truncates to ~40K chars)
- `scripts/run_memory_extraction.py` — Python entrypoint for orchestrator/subagent use

## Downstream

- Replaces manual parts of `export_agent_conversations.py`
- Replaces Heartbeat Task 7 (memory consolidation) partially
- Orchestrator's `consolidate_agent_memory()` should be refactored to call this system at handoff time
