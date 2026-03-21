---
primitive: task
status: open
priority: medium
created: 2026-03-21
owner: belam
depends_on: [orchestration-engine-v2-temporal-autoclave]
upstream: [task/orchestration-engine-v2-temporal-autoclave, decision/codex-engine-modes-as-primitives]
downstream: [task/codex-engine-v3-temporal-mcp-autoclave]
tags: [orchestration, monitoring, real-time, autoclave, v3, dashboard]
---

# Orchestration V3: Real-Time Monitoring Suite

## Overview

Build a real-time monitoring layer on top of the V2-temporal SQLite overlay. The temporal overlay stores state transitions, agent context, and pipeline history — V3 makes that data *visible* in real time.

**Open question:** Is this a standalone monitoring suite, a codex engine upgrade (e0a becomes a live view), or both? Design should answer this before implementation.

## Design Space

### Option A: Standalone Monitoring Suite
- Separate process/daemon that watches the SQLite WAL for changes
- Renders to terminal (tmux pane), web dashboard, or canvas
- Independent of codex engine — pure observation layer
- Pro: clean separation, can run without engine
- Con: another process to manage

### Option B: Codex Engine Live Mode (e0a)
- `e0a` coordinate becomes a live-updating dashboard within engine context
- `before_prompt_build` hook injects current dashboard state per-turn
- No daemon — reactive, renders on each agent turn
- Pro: zero new infrastructure, agents see it automatically
- Con: not truly real-time (only updates on agent turns)

### Option C: Hybrid (Recommended?)
- Codex engine `e0a` provides per-turn dashboard injection (Option B)
- Lightweight watcher process for human-facing real-time view (Option A)
- Watcher uses same SQLite DB — no duplication
- Canvas rendering for Shael's live view via OpenClaw canvas tool

## Features (Design Phase — Not Committed)

### 1. Pipeline Timeline Visualization
- Stage progression with timestamps and durations
- Bottleneck highlighting (stages that took longest)
- Time-travel scrubber: "show me the state at 14:00 UTC"
- Source: `temporal_overlay.get_timeline()`, `get_stage_durations()`

### 2. Agent Activity Monitor
- Which agents are active, what they're working on
- Presence heartbeats with TTL-based liveness
- Context accumulation: decisions made, flags resolved, learnings captured
- Source: `temporal_overlay.heartbeat()`, `get_agent_context()`

### 3. F-label ↔ R-label Causal Graph
- Show how filesystem diffs (F-labels) cascade to view changes (R-labels)
- Time-travel undo: reverting F1 shows which R-labels would change
- Visual diff: "if we undo this state change, here's what shifts"
- **Key integration:** F-label reverts must trigger R-label re-renders (from Phase 2 feedback)

### 4. Scoped Views via Persona Primitives
- Global coordinates always valid
- View filter controlled by orchestration, not by agent
- `i1` (architect) sees design/review state, `i2` (critic) sees review queue, `i3` (builder) sees implementation backlog
- Dashboard adapts presentation to persona without changing coordinate space
- Dispatch payload includes view filter metadata

### 5. Cross-Pipeline State
- Multiple pipelines on a single dashboard
- Dependency graph between pipelines
- Gate status visualization (what's blocking what)
- Source: `temporal_overlay.get_dashboard()`

## Integration Points

### With Codex Engine V3 (t4)
- MCP server could serve dashboard as a resource: `mcp://belam/codex/e0a`
- Multi-pane rendering (t4 feature) naturally includes dashboard pane
- `.codex` reactive materialization could trigger on SQLite WAL changes

### With Persistent Extend (t8)
- Monitoring suite itself could be a namespace: `e31 a.autoclave`
- Dashboard views as primitives — editable, versionable, persona-scoped

### With Codex Cockpit Plugin
- `before_prompt_build` already injects supermap — could inject dashboard summary too
- Per-turn context: "since your last turn: 2 stages completed, 1 handoff pending"

## Open Questions (for architect/critic)

1. Standalone daemon vs codex engine integration vs hybrid?
2. Canvas rendering (OpenClaw canvas tool) for Shael's real-time view — worth the complexity?
3. Should time-travel undo be a first-class engine operation (`e1z` or similar)?
4. How does the monitoring suite handle multiple concurrent human viewers?
5. SQLite WAL polling interval vs inotify for change detection?

## Acceptance Criteria (Draft)

- [ ] Design decision: standalone / engine / hybrid
- [ ] Real-time pipeline state visible to human (Shael)
- [ ] Agent-scoped views via persona primitives
- [ ] F-label → R-label causal chain for undo operations
- [ ] Time-travel with visual output
- [ ] Cross-pipeline dependency visualization

## Dependencies

- Orchestration V2-Temporal Phase 2 (F/R label integration, persona-scoped views)
- Codex Engine V2 (dense grammar, coordinate system)
- Persona primitives (i1-i3) from t8

## Design Conversation
Shael + Belam, 2026-03-21 18:02 UTC. Shael raised real-time monitoring as illustration-worthy, questioned whether it's a monitoring suite or codex engine upgrade. Also provided key Phase 2 feedback on V2-temporal: time-travel should use F/R labels with causal coupling, and autoclave views should use global coords with persona-filtered presentation.
