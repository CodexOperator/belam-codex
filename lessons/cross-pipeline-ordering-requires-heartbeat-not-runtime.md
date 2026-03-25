---
primitive: lesson
date: 2026-03-25
source: main session 2026-03-25T03:11
confidence: high
upstream: [decision/heartbeat-priority-order-infra-tasks, decision/orchestration-fire-and-forget-dispatch]
downstream: []
tags: [instance:main, pipeline, orchestration, depends_on, heartbeat]
---

# cross-pipeline-ordering-requires-heartbeat-not-runtime

## Context

Planning to launch 6 sequential backtesting subtasks (s1→s2→s3→s4→s5→s6) via the builder-first pipeline template. Shael asked whether launching all 6 pipelines at once with upstream/downstream dependency fields would guarantee execution order.

## What Happened

The `depends_on` field on a task is only checked at **launch time** by heartbeat Task 5 — once a pipeline is created and kicked off, it runs independently. There is no cross-pipeline dependency engine in `pipeline_orchestrate.py`. Launching all 6 simultaneously would dispatch 6 builders concurrently, ignoring task dependencies entirely.

## Lesson

Cross-pipeline ordering is enforced at the *launch gate* (heartbeat checks `depends_on` before creating a pipeline), not at runtime. Once a pipeline is running, it executes independently regardless of other pipelines' status.

## Application

- Never assume `depends_on` on a task file prevents concurrent execution if all pipelines are pre-created.
- For ordered subtask chains: rely on heartbeat's sequential launch (one pipeline at a time, next launched only after previous is `done`).
- If tighter inter-pipeline chaining is needed, build explicit cross-pipeline completion hooks into `pipeline_orchestrate.py` (mark as a separate infrastructure task).
- Tightening heartbeat interval is the pragmatic lever for faster auto-chaining without new code.
