---
primitive: task
status: open
priority: medium
created: 2026-03-21
owner: belam
depends_on: [build-orchestration-engine-v1]
upstream: [decision/orchestration-architecture, decision/codex-engine-v2-dense-alphanumeric-grammar]
downstream: []
tags: [orchestration, engine, temporal, spacetimedb, autoclave, v2]
---

# Orchestration Engine v2: Temporal State, Persistent Agents, Autoclave View

## Overview

After orchestration v1 stabilizes (codex-native pipeline automation), back it with a temporal database and enable real-time multi-agent coordination. This is where orchestration becomes reactive rather than poll-based.

## 1. SpacetimeDB Temporal State Layer

- Evaluate SpacetimeDB vs SurrealDB vs EventStoreDB for orchestration state
- Pipeline state → temporal table with automatic diff generation
- Agent turns → temporal log (replaces JSONL conversation exports)
- Handoff records → temporal events with causal ordering
- Gate conditions as temporal queries: "did event X happen before event Y?"

## 2. Persistent Agents + Subscriptions

### Current Problem
Each agent session is fresh — spawned, runs, dies. Context must be reconstructed every time.

### Target
- Agents run as persistent processes with continuous SpacetimeDB subscriptions
- Real-time diffs dispatch immediately (no session load overhead)
- Hook registrations and tool access persist continuously
- Context *resets* per handoff (fresh reasoning) but *process* stays alive
- SpacetimeDB subscriptions feed state changes directly into agent context

### Architecture
```
SpacetimeDB (temporal state store)
    ↕ subscriptions / writes
Orchestration Engine v2
    ↕ state deltas as R-label diffs
Persistent agent (continuous process)
    ↕ actions via e0
Pipeline state transitions
```

## 3. Shared Autoclave View

### Purpose
When multiple agents work on the same pipeline simultaneously, they need coordinated context.

### Design
- Orchestration engine detects co-active agents via SpacetimeDB subscription
- Context shifts to shared-view mode (R-label drops to show mode change)
- Both agents see same state diffs, minimizing divergence
- Critic's diffs stream into architect's context as they arrive
- No polling — temporal subscriptions push diffs
- Conflict resolution: last-write-wins with causal ordering from temporal DB

## 4. Temporal Handoffs

### Beyond v1 checkpoint-and-resume
- Handoff history is a temporal log — can replay any handoff chain
- "Show me what architect→critic→builder did on p3" = temporal query
- Rollback to any handoff point: temporal rewind, not file-based undo
- Causal ordering ensures handoff dependencies are respected across parallel pipelines

## Acceptance Criteria

- [ ] SpacetimeDB evaluation complete (vs SurrealDB, EventStoreDB)
- [ ] Temporal state prototype with diff generation for pipeline state
- [ ] Persistent agent proof of concept (process stays alive across handoffs)
- [ ] Subscription-driven context injection working
- [ ] Shared autoclave view between 2 co-active agents
- [ ] Temporal handoff replay: query handoff chain history
- [ ] Temporal rollback: rewind to previous handoff state

## Dependencies
- Orchestration Engine v1 must be stable
- Codex Engine v2 (dense grammar, RAM state)
- `tasks/temporal-interaction-llm-gaming.md` — shares SpacetimeDB evaluation

## Notes
- This is the bridge between "scripts that run agents" and "agents that coordinate themselves"
- Persistent agents are the prerequisite for true autonomous operation
- Autoclave view is what makes multi-agent pipelines feel like one coherent system rather than sequential handoffs
