---
primitive: lesson
date: 2026-03-20
source: relationship-mapper-burn-session
confidence: high
upstream: [decisions/agent-session-isolation, decision/orchestration-architecture]
downstream: []
tags: [infrastructure, agents, openclaw, session-routing]
---

# openclaw agent CLI Routes to Active Session, Not Isolated

## Context

Building the relationship mapper, tried using `openclaw agent --agent main --session-id mapper-xxx` from a background Python script to spawn isolated judgment tasks.

## What Happened

All task messages routed into the coordinator's active session instead of creating isolated sessions. The `--session-id` flag doesn't create true isolation — it still targets the same agent endpoint. Background script tasks appeared as incoming messages in the live coordinator chat.

## Lesson

`openclaw agent --agent main` always routes to the active main session. Use `sessions_spawn` from within the coordinator for ephemeral subagent work.

## Application

- **Don't:** Spawn `openclaw agent --agent main` from background scripts while coordinator is active
- **Do:** Use `sessions_spawn` tool for parallel subagent work (proven: 8 parallel Sonnet subagents, ~10s each)
- **Alternative:** Use `--agent architect` or `--agent critic` if CLI spawning is needed (they have separate session spaces)
