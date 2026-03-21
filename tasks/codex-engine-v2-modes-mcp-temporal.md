---
primitive: task
status: open
priority: high
project: multi-agent-infrastructure
depends_on: []
tags: [engine, codex, modes, mcp, temporal, spacetimedb, primitives]
created: 2026-03-21
---

# Codex Engine v2: Modes as Primitives, MCP Integration, Temporal Architecture

## Overview

Unify the codex engine so that modes, commands, tool calls, and orchestration actions all follow the same primitive pattern. Integrate MCP compatibility using codex-native token-efficient formats. Back the state layer with a temporal database (SpacetimeDB) using `.codex` files as the sync format.

## Design Principles

1. **Everything is a primitive** — modes, commands, extensions, even the engine's own config
2. **Same pattern everywhere** — coordinates, frontmatter, R-label diffs, .codex serialization
3. **The lathe builds the lathe** — extend mode (`-x`) uses primitives to modify the primitive set
4. **Token efficiency is non-negotiable** — all formats optimized for LLM context injection

---

## 1. Modes as Primitives

### Current State
- CLI flags (`-g`, `-e`, `-n`, `--depth`, `--graph`) modify engine behavior
- No unified "mode" concept — each flag is ad-hoc

### Target State
- Modes are primitives with their own namespace (e.g., `mo:` prefix or nested under engine)
- Each mode primitive defines: behavior spec, applicable namespaces, transformations
- `-o` becomes orchestration mode → `mo:orchestrate` or similar coordinate
- Modes compose: `-o -g` = orchestration mode with graph view

### Mode Categories (initial)

| Mode | Coordinate | Description |
|------|-----------|-------------|
| orchestrate | `mo1` | Pipeline orchestration — dispatch, gate check, handoff |
| edit | `mo2` | Create/modify primitives — frontmatter editing, status transitions |
| extend | `mo3` | Meta-mode — add new categories, namespace prefixes, integrate custom code |
| view | `mo4` | Read-only rendering — current default behavior |
| diff | `mo5` | R-label diff view — show transformations rather than full state |

### Implementation
- New namespace prefix in `codex_engine.py`: `'mo': ('modes', 'modes', None)`
- Mode primitives in `modes/*.md` with frontmatter defining behavior
- Engine reads mode primitive to determine rendering/action behavior
- Composable: multiple modes can be active (priority-ordered)

---

## 2. Extend Mode (`-x`) — The Meta-Layer

### Purpose
Use the engine to modify the engine. Adding a new primitive type, namespace, or category is itself an extend-mode operation.

### Operations
- `belam -x category <name>` → create new primitive category with namespace prefix
- `belam -x namespace <prefix> <type> <dir>` → register new namespace in engine
- `belam -x integrate <path>` → integrate external code/plugin into engine resolution
- `belam -x template <type>` → create frontmatter template for new primitive type

### Self-Documentation
Each extend operation creates a primitive trail — you can `belam mo3` to see all extensions that have been applied to the engine.

---

## 3. Persistent Agents + Temporal DB Architecture

### Why Persistent (Revised)

With SpacetimeDB backing, persistent agents are superior to fresh sessions:
- Real-time diffs dispatch immediately (no session load overhead)
- Diff-minimalist injection = tiny per-turn cost
- Hook registrations and tool access persist continuously
- Context resets per handoff (not process restarts)
- SpacetimeDB subscriptions feed directly into agent state

### Architecture

```
SpacetimeDB (temporal state store)
    ↕ subscriptions / writes
.codex files (materialized views)
    ↕ read on each turn
before_prompt_build hook (context injection)
    ↕ state deltas as R-label diffs
Persistent agent (continuous process)
    ↕ actions
pipeline_orchestrate.py → SpacetimeDB writes
```

### Shared Autoclave View

When multiple agents work on the same pipeline:
1. Hook detects co-active agents via SpacetimeDB subscription
2. Context shifts to shared-view mode (R-label drops to show mode change)
3. Both agents see same state diffs, minimizing divergence
4. Critic's diffs stream into architect's context as they arrive
5. No polling — temporal subscriptions push diffs

### SpacetimeDB Integration Points
- Pipeline state → temporal table with automatic diff generation
- Agent turns → temporal log (replaces JSONL conversation exports)
- Handoff records → temporal events with causal ordering
- `.codex` files as materialized views of temporal queries

---

## 4. MCP Compatibility (Codex-Native)

### Standard MCP Problem
- JSON-RPC transport is verbose
- Resource descriptions waste tokens explaining structure
- Examples in docs are repetitive

### Codex-Native MCP

Our MCP server returns resources in codex engine format:
- `mcp://belam/pipelines/v4` → returns pipeline primitive (compact frontmatter + status)
- `mcp://belam/codex/t1` → returns task primitive at coordinate t1
- `mcp://belam/modes/orchestrate` → returns mode primitive spec

### R-Label Diffs as Usage Docs

Instead of:
```
Tool: pipeline_status
Description: Returns the current pipeline status
Example: pipeline_status(version="v4") → { status: "phase1_complete", ... }
```

Provide:
```
[Δ t1.status] open → in_pipeline
[Δ p3.stage] architect_design → critic_review  
[+ handoff] 20260321T034326 architect→critic
```

The client LLM sees the *transformation* — what changed — rather than an explanation of what the tool does. Way more compressed, way more actionable.

### .codex File Interaction

MCP server is itself addressable through the engine:
- `belam x:mcp` → shows MCP server state, registered resources
- MCP resources resolve through the same coordinate system
- External MCP clients (Cursor, Claude Desktop) get codex-native representations

---

## 5. .codex Files as Sync Layer

### Current State
- `.codex` files are supermap snapshots injected at boot
- Static — generated, not reactive

### Target State
- `.codex` files are materialized views of SpacetimeDB temporal queries
- Updated reactively when state changes (subscription-driven)
- Agents read `.codex` files via hooks — never query DB directly
- Format remains token-efficient (same as current supermap)
- Temporal indexing means `.codex` files can represent "state at time T" or "diffs since time T"

### Sync Protocol
1. Agent action → write to SpacetimeDB
2. SpacetimeDB subscription fires → materialize updated `.codex` view
3. Next agent turn → `before_prompt_build` reads fresh `.codex`
4. Agent sees temporal diff in context
5. No daemon needed — materialization triggered by DB subscription callbacks

---

## 6. Inline Artifact Rendering

### Bug
Canvas artifacts rendered as inline CLI output don't respect mobile viewport width.

### Fix Options
- Use canvas with responsive HTML + viewport meta tag for complex artifacts
- Keep inline output narrow (~40 chars) for mobile terminal compatibility
- Add `--mobile` flag to engine rendering for narrow-width output mode

---

## Acceptance Criteria

- [ ] Modes namespace registered in codex_engine.py
- [ ] At least 3 mode primitives created (orchestrate, edit, extend)
- [ ] `-x` extend operations create primitive trail
- [ ] MCP server prototype returning codex-native resources
- [ ] R-label diff format spec documented
- [ ] SpacetimeDB evaluation complete (vs SurrealDB, EventStoreDB)
- [ ] `.codex` reactive materialization prototype
- [ ] Persistent agent + temporal subscription proof of concept
- [ ] Shared autoclave view working between 2 agents
- [ ] Mobile-friendly artifact rendering

## Dependencies
- `tasks/temporal-interaction-llm-gaming.md` — shares SpacetimeDB evaluation
- `research-openclaw-internals` pipeline — hook architecture findings

## Notes
- Pydantic for state validation: deterministic serialization → idempotent operations. Use for pipeline state models to catch malformed state early.
- "Using the lathe to build a better lathe" — extend mode is the meta-primitive that makes the system self-evolving.
