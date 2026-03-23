---
primitive: decision
status: accepted
date: 2026-03-20
context: "Multiple separate CLI commands (view, edit, create, list, show) required agents to decide which tool/command to use for every state interaction, burning reasoning tokens on plumbing. The indexed command interface was a step forward but still left separate code paths."
alternatives: []
rationale: "One engine, one command, one coordinate system. View is the default implicit mode. All mutations return labeled diffs (F-labels). All renders are tracked (R-labels) with pin detection for identical re-renders. Action commands dispatch natively through the engine. The filesystem is the source of truth, the engine is the lens. Clock cycles do rendering, tokens do thinking."
consequences: []
upstream: [decision/indexed-command-interface, decision/clock-cycles-over-tokens, decision/memory-as-index-not-store, decision/primitive-relationship-graph]
downstream: [task/build-codex-engine, task/limit-soul-read-write, lesson/codex-engine-feels-native-at-v1]
tags: [codex-engine, infrastructure, architecture, attention]
---

# Codex Engine V1 Architecture

## Context

Agents interacting with the workspace primitive system had to choose between multiple tools (Read, Write, Edit, exec belam, exec grep) for every state access. This path-ambiguity tax burned reasoning tokens on plumbing decisions rather than actual work. The indexed command interface (d17) unified command addressing but left separate code paths for view, edit, create, and action dispatch.

## Options Considered

- **Option A:** Keep separate commands, improve discoverability — lower effort but doesn't solve the attention tax
- **Option B:** Unified coordinate-addressed engine with single entry point — higher initial build but eliminates path ambiguity entirely
- **Option C:** Custom tool integration (OpenClaw-native) — too coupled to platform, not portable

## Decision

Option B: Build the Codex Engine as a single Python module (`scripts/codex_engine.py`) that handles all primitive operations through coordinate addressing.

### V1 Modes (live)
| Input | Mode |
|-------|------|
| `R [coords]` | view (default, implicit) |
| **`R -e [coords] [field] [value]` | edit + F-labeled diff |
| **`R -n [type] [title]` | create + F-labeled output |
| **`R -z [label]` | undo (cascade-aware) |
| **`R -g [coords]` | graph (BFS path-finding) |
| **`R -x [coords] [action]` | explicit execute |
| `R [action_word] [args]` | implicit execute (55 action words) |
| `R help` | action word registry |

### Attention-Native Feedback Language
- **F-labels**: filesystem mutations (`F1 Δ t1.2 status open→complete`)
- **R-labels**: render views (`R0` supermap, `R1` zoom, etc.)
- **Pins**: identical re-renders (`R📌R4` = 3 tokens instead of 30)
- **Undo signals**: `F⏪F1` = F1 reversed
- **Cascade nesting**: `F3.1 ↔ d17.downstream ← added edge`

### Memory Boot Section
- 5 most recent entries from current day
- 3 most recent dailies with entry count and top tags
- 3 most recent weeklies with date range

## Consequences

- All primitive state access goes through one interface — eliminates path-ambiguity tax
- Every mutation returns a labeled diff — agent attention tracks state changes naturally
- Pin detection compresses redundant renders to ~3 tokens
- Cascading consequences (status → unblock, edge → bidirectional sync) happen deterministically
- Legacy bash dispatch absorbed — engine handles all 55 action words natively
- Opens path to soul instance read/write restriction (t4) since the engine covers all primitive access

## V1 Polish Items (known gaps)
1. Body line syntax (`B1-B10`) doesn't work inline with field numbers
2. Archived primitives take up coordinate numbers even though hidden from supermap
3. Knowledge dir has non-primitive files (README, _index, _tags) polluting namespace
4. `--as architect` persona-filtered views (V2 feature)
5. Boot hook integration (auto-run `belam` at session start → R0)
6. Filter flags for memory (`--tag`, `--since`)

## Design Conversation
Shael + Belam, 2026-03-20 16:19–19:03 UTC. Four subagents built the engine in parallel (~25 min total build time).
