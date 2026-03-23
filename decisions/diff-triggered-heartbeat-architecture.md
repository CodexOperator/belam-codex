---
primitive: decision
slug: diff-triggered-heartbeat-architecture
title: Diff-Triggered Heartbeat Architecture
importance: 4
tags: [instance:main, render-engine, heartbeat, diff, architecture]
created: 2026-03-23
---

# Decision: Diff-Triggered Heartbeat Architecture

## Context
The render engine produces R/F label diffs when files change via inotify. Previously these diffs were passive — accumulated until a user message triggered a turn. The coordinator would only see them on the next organic conversation turn.

## Decision
Add a `HeartbeatTrigger` thread to `codex_render.py` that:
- Polls every 5 seconds for accumulated F-label diff count
- When 10+ F-label diffs accumulate within the window, fires a `POST /hooks/wake` to the OpenClaw webhook endpoint
- Wakes the main session as a system event (not a user message)
- Coordinator processes the diffs, may take action, but doesn't message the user unless something is actionable

## Rationale
- Gives the coordinator real-time awareness of memory extractions, pipeline state changes, and file updates
- Avoids polling loops — the render engine is already watching files, so it's the natural place to emit wake signals
- Threshold of 10 F-labels prevents spurious wakes from single small writes; 5s poll keeps latency acceptable
- Keeps the event type clearly distinct from user messages (system event, not user prompt)

## Implementation
- `codex_render.py`: `HeartbeatTrigger` class, `_load_hook_config()`, started/stopped in engine lifecycle
- OpenClaw config: `hooks.enabled: true`, `hooks.token` set, `hooks.path: /hooks`
- Committed: ceb8d260

## Tradeoffs
- Could create feedback loops (response writes files → inotify → diff → wake → ...). Mitigated by threshold and the fact that wake only fires once per batch.
- Coordinator must distinguish "diff wake" from "user message" — system event format handles this naturally.

## Related
- upstream: codex-engine-v2-live-diff-architecture
- upstream: render-engine-pid-file-and-force-flag
- downstream: r-f-label-split-by-agent-role
- downstream: webhook-hooks-enabled-for-diff-heartbeat
