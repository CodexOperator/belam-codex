---
primitive: lesson
date: 2026-03-24
source: heartbeat orchestration observation
confidence: high
importance: 3
upstream: [decision/orchestration-fire-and-forget-dispatch]
downstream: []
tags: [instance:main, pipelines, heartbeat, state-management, orchestration]
---

# pipeline-state-not-updated-after-fire-and-forget-kick

## Context

Heartbeat was running the infrastructure pipeline queue (Task 5). At 09:18, it archived containerize-openclaw-workspace and claimed it auto-kicked to phase2. At 09:48 (30 minutes later), the same pipeline still showed `phase1_complete` in both the supermap and on disk.

## What Happened

The fire-and-forget dispatch (PID 3209915) appeared to succeed but the pipeline state file was not updated to reflect the new stage. The pipeline appeared to "kick" but the state on disk remained at `phase1_complete`. The next heartbeat re-archived it as if nothing had happened.

## Lesson

Fire-and-forget pipeline kicks do not guarantee state advancement — the dispatched agent may not write back the new state in time, or may fail silently. Heartbeats must re-check and re-archive if state hasn't advanced after a kick.

## Application

- After kicking a pipeline to the next phase, do not assume the state is updated. On the next heartbeat, verify the actual file status before launching new tasks.
- Consider adding a post-kick verification step or a "pending_kick" marker to avoid duplicate dispatches.
- The heartbeat re-archive behavior is correct: treat stale phase1_complete as actionable regardless of prior kick.
