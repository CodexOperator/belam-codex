---
primitive: decision
date: 2026-03-20
status: accepted
upstream: []
downstream: []
tags: [instance:main, memory-extraction, automation, architecture, hook]
---

# auto-memory-extraction-architecture

## Decision

Implement automated session memory extraction as a combined workspace hook that fires on `/new` and `/reset` commands — saving session context and spawning sage for primitive extraction in one sequential flow.

## Context

Shael asked for automated extraction of memories/lessons/decisions from every session. Original implementation used `agent:bootstrap` event + separate bundled `session-memory` hook. This caused silent failures (bash script race with `.reset.*` file renaming) and the split trigger made debugging hard.

## Architecture (Current — v2)

Single workspace hook (`hooks/memory-extract/handler.ts`) fires on `command` event (new/reset):

1. **Save session context** — writes `memory/YYYY-MM-DD-HHMM.md` summary (replaces bundled `session-memory` hook, now disabled)
2. **Extract memories** — resolves session file from event context (handles pre/post-rename timing), runs `extract_session_memory.sh`, spawns sage agent in background

The hook resolves the session file from `event.context.previousSessionEntry.sessionFile`, trying the original path first and falling back to `.reset.*` — avoiding the race condition.

**Agent:** sage (formerly code-tutor — session key updated from `agent:code-tutor:main` to `agent:sage:main`)

**CLI:** `R extract [instance] [--file PATH] [--bg]` — routes through codex engine (`-x` flag)

**Logging:** All errors to `logs/memory-extract.log`

## Options Rejected

1. **Separate triggers** (bundled session-memory on `command` + custom on `agent:bootstrap`) — race condition, silent failures, hard to debug
2. **Marker file approach** (hook writes marker → agent reads on boot) — unnecessary indirection
3. **Direct spawn from hook during lock** — lock collision with active session

## Downstream

- Bundled `session-memory` hook: **disabled** (replaced by this hook)
- Orchestrator's `consolidate_agent_memory()`: fallback for sub-agent sessions at handoff time
- `embed_primitives.py`: **archived** — replaced by codex engine supermap (`R boot`)
