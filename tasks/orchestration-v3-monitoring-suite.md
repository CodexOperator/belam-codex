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

**Direction:** Option C (hybrid) confirmed by Shael. Research pipeline needed to evaluate SQLite WAL as the reactive change-detection mechanism.

## Architecture: Option C (Hybrid)

- Codex engine `e0p{N}.v{M}` provides per-turn dashboard injection for agents
- Lightweight watcher process for human-facing real-time view (SQLite WAL-based)
- Watcher uses same SQLite DB — no duplication
- Canvas rendering for Shael's live view via OpenClaw canvas tool
- **Research needed:** Can SQLite WAL provide reliable change notification for live streaming?

## Coordinate Design: `.v` (View) Namespace

Use `v` for "view" — viewing *someone else's* state rather than your own. The `.v` suffix on a pipeline coordinate selects the view type.

### View Types

| Coordinate | View | Description |
|------------|------|-------------|
| `e0p1.v1` | Turn-by-turn | Snapshot dashboard injected per agent turn |
| `e0p1.v2` | Live diff stream | Continuous diffs as they land between agents |
| `e0p1.v3` | Timeline | Stage progression with durations and bottlenecks |
| `e0p1.v4` | Agent context | Decisions, flags, learnings for pipeline agents |
| `e0p{N}.v{M}` | (future) | Extensible — new view types register here |

### Bare Forms
- `e0v1` = global turn-by-turn view (all pipelines)
- `e0p1.v1` = turn-by-turn view scoped to pipeline 1
- `e0v` or `e0.v` = list available view types

### Why `v` not `a`
- `a` for "autoclave" is an internal name — `v` for "view" is what it actually does
- `v` implies viewing *external* state (another agent's work, another pipeline's progress)
- View types are extensible: `.v1`–`.vN` grows naturally as we add visualization modes
- Consistent with the principle: letters route to namespaces, numbers select from lists

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
- **2026-03-21 18:02 UTC:** Shael raised real-time monitoring, questioned suite vs engine upgrade. Provided Phase 2 feedback on V2-temporal: F/R label causal coupling, global coords with persona-filtered views.
- **2026-03-21 18:28 UTC:** Shael confirmed Option C (hybrid). Designed `.v` namespace: `e0p1.v1` (turn-by-turn), `e0p1.v2` (live diff stream), extensible to `.v3`+. Chose `v` over `a` — "view" is what it does, "autoclave" is internal. Research pipeline needed for SQLite WAL change detection. Dot binds view type to pipeline coordinate, space separates operations.
