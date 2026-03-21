# Orchestration Engine V1 — Design Document

## Core Identity
On-demand CLI engine with persistent `.codex` state buffer. No daemon — thick CLI with warm state.

## Format
All engine state stored in `.codex` files — native to the codex engine's coordinate-addressable format. Readable by agents when injected as context, parseable by the engine for mutations.

### State File: `state/orchestration.codex`
```
# orchestration.codex — Engine State

## agents
╶─ a1  architect  idle  ctx:hash7f3a  synced:03:05
╶─ a2  builder    active  ctx:hash9b2c  synced:02:58

## pending_diffs
╶─ Δ1  t1  a2→*  [R:status] [F1:+features] [F2:~deps]

## flow
╶─ p1  validate-scheme-b  local_analysis_complete  gate:waiting
```

## Diff Protocol
On-write: when an agent modifies a primitive, engine computes + stores diff immediately.
On-read delivery: receiving agent pulls pending diffs on spawn/refresh.

### Diff Format
```
[SYNC t1 ΔR3→R4]
  status: active → complete       [R]
  F1: +## V2 Features             [F]
  F2: ~dependencies (3 changed)   [F]
  edges: +→d8, -→t3               [R]
```

### SYNC_READY Protocol
- Agent writes diffs as it works (partial state visible)
- Agent writes SYNC_READY marker when its work unit is complete
- Receiving agents are instructed to hold/accumulate diffs until SYNC_READY
- Tests temporal patience in classical LLM architectures

## Commands (V1)
- `sync --generate` — compute diffs for changed primitives
- `sync --deliver <agent>` — format pending diffs as R/F-labels for target
- `dispatch <agent> <task>` — spawn + register in state
- `flow --check` — gate evaluation + transition logic
- `status` — current engine state overview

## Integration
- Codex Engine: reads primitive state, shares .codex format
- pipeline_orchestrate.py: flow logic migrates here
- pipeline_autorun.py: automation logic migrates here

## Research Pipelines (parallel)
1. OpenClaw internals — session routing, hooks, extension points
2. Off-the-shelf orchestration — MCP servers, agent frameworks, event-driven comms

## Future: Temporal Awareness Experiment
- Test classical LLM patience under async diff streams
- Persona-loaded agents with explicit patience protocols
- Potential spiking-transformer integration surface discovery
- Task: spiking-transformer-integration (to be created)

## Dependencies
- Codex Engine V1 (complete)
- .codex format parser (extend from codex_engine.py)
