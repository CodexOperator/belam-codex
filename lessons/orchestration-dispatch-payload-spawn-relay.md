---
primitive: lesson
date: 2026-03-22
source: session b8a4b4a1 2026-03-21
confidence: high
importance: 3
upstream: [decision/orchestration-fire-and-forget-dispatch, lesson/pipeline-orchestrate-blocking-agent-wake]
downstream: []
tags: [instance:main, orchestration, pipeline, sessions_spawn, dispatch]
promotion_status: promoted
doctrine_richness: 10
contradicts: []
---

# orchestration-dispatch-payload-spawn-relay

## Context

Running autonomous multi-pipeline dependency resolution (Engine V2 → Orch V3 → Engine V3). The orchestration engine V2 (`orchestration_engine.py`) handles all gate logic, stage transitions, and dispatch payload generation, but doesn't natively spawn subagents — the spawn call must be issued from the main session.

## What Happened

Used `orchestration_engine.py dispatch-payload <version> <agent>` to get a structured JSON spawn payload with the full task prompt, memory protocol, pre/post actions, and stage context. Then passed that payload directly into `sessions_spawn` as the `task` parameter. The orchestration engine tracked state; the main session acted as spawn relay.

## Lesson

`dispatch-payload` is the bridge between orchestration engine logic and sessions_spawn: the engine generates the *what*, the main session executes the *how*. This is the interim pattern until Orch V3 closes the autonomous relay loop.

## Application

When running multi-stage pipeline chains autonomously:
1. Call `orchestration_engine.py dispatch-payload <ref> <agent>` to get structured task prompt
2. Pass the payload's `spawn.task` field into `sessions_spawn` with appropriate model/label
3. Wait for completion event, then call `orchestration_engine.py complete <ref> <stage>` to advance state
4. Repeat for each stage (architect → critic_design_review → builder → critic_code_review)

This pattern makes the orchestration engine the single source of truth for pipeline state while keeping spawn logic in the session layer. Orch V3's automation goal is to close this loop so no manual relay is needed.
