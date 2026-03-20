---
primitive: task
status: open
priority: critical
created: 2026-03-20
owner: belam
depends_on: []
upstream:
  - decision/indexed-command-interface
  - decision/memory-as-index-not-store
  - decision/clock-cycles-over-tokens
  - decision/primitive-relationship-graph
downstream: []
tags: [infrastructure, cli, codex-engine, primitives]
---

# Build Codex Engine

## Description

Unified primitive navigation, viewing, and editing system for the belam CLI. Replaces all separate view/edit/create commands with a single coordinate-addressed interface. One command, five modes, zero filesystem awareness needed by the agent.

The engine renders live views from the primitive filesystem, supports field-indexed editing with cascading consequences, and returns diffs on every mutation. View is the default implicit mode.

## Design Spec

### Namespace Map

| Prefix | Type | Example |
|--------|------|---------|
| `p` | pipelines | `p1` |
| `w` | workspaces (was projects) | `w2` |
| `t` | tasks | `t3` |
| `d` | decisions | `d12` |
| `l` | lessons | `l7` |
| `c` | commands | `c5` |
| `k` | knowledge | `k1` |
| `s` | skills | `s2` |
| `m` | memory entries | `m15` |
| `md` | daily memory | `md1` |
| `mw` | weekly memory | `mw2` |

### Modes

| Input | Mode |
|-------|------|
| `belam [coords]` | view (default, implicit) |
| `belam -e [coords] [field] [value]` | edit + diff |
| `belam -g [coords]` | graph (local subgraph) |
| `belam -x [coords] [action]` | execute (wraps existing scripts) |
| `belam -n [type] [title]` | create + scaffold |

### Supermap (boot view, `belam` with no args)

Compact ASCII tree of all primitive types with one-line summaries. Memory section shows:
- 5 most recent entries from current day
- 3 most recent dailies (entry count + top tags)
- 3 most recent weeklies (date range + top tags)

### Zoom View (`belam <coords>`)

Field-indexed display of one or more primitives. Supports:
- Single: `belam t3`
- Range: `belam t1-t3`
- Field selection: `belam t1-t3 1 3 5` (title, priority, tags)
- Cross-type: `belam t1 d5 l3`
- Body as line-indexed: `B` for all, `B1-B15` for lines

### Edit (`belam -e`)

Same coordinate system as view. Returns diff showing what changed.
- Single field: `belam -e p1 2 'phase2_running'`
- Multi-field: `belam -e m3 1 'new title' 3 'new desc'`
- Cross-type: `belam -e t1 3 'high' p1 4 'phase2_running'`

### Graph View (`belam -g`)

Local subgraph around specified nodes via upstream/downstream frontmatter.
- `belam -g d2` — all direct connections
- `belam -g d2 --depth 3` — 3 hops
- `belam -g d2 l5` — paths between two nodes

### Execute (`belam -x`)

Wraps existing action scripts (run, kickoff, analyze, revise, etc.) through coordinate addressing.
- `belam -x p1 run` → runs experiments for pipeline p1
- `belam -x p1 analyze` → kicks off analysis

### Create (`belam -n`)

Scaffolds new primitives with type-appropriate frontmatter and skeleton body.
- `belam -n t 'Build something'` → creates task
- Auto-detects related primitives by tag overlap
- Runs embed_primitives after creation

### Attention-Native Feedback Language

All engine output uses labeled diffs as attention anchors:

- **F-labels** (filesystem mutations): `F1 Δ p1.4 phase1_complete→phase2_running`
- **R-labels** (render views): `R1 [rendered view content]`
- **Undo**: `F⏪F1` — signals F1 is reversed, no re-dump needed
- **Pin**: `R📌R1` — identical to R1, zero new tokens
- **Cascade nesting**: `F1 Δ t3.1 status open→complete` / `  └─ F1.1 ⚡ t4 unblocked`
- **Genesis render**: `R0` — the supermap at boot. All subsequent R-labels diff from last R.
- Labels are sequential per session: F1, R1, F2, R2, F3...
- Agent can reference labels in reasoning ("the state before F2") without re-scanning context

This is the interface language between the engine and agent attention — minimal tokens, maximum semantic payload.

### V1 Features (this build)

- [ ] Core rendering engine (supermap, zoom, field-indexed display)
- [ ] Namespace resolution (coords → filesystem paths)
- [ ] Attention-native feedback language (F-labels, R-labels, pins, undo signals, cascade nesting)
- [ ] Edit with cascading consequences (status changes trigger downstream checks)
- [ ] Bidirectional edge updates on relationship edits
- [ ] Type-aware validation (reject invalid stage transitions, etc.)
- [ ] Diff-on-mutation (every edit returns F-labeled delta)
- [ ] Graph view (local subgraph rendering)
- [ ] Execute mode (wraps existing scripts)
- [ ] Create mode (wraps existing scaffold)
- [ ] Memory boot section (today 5 + 3 dailies + 3 weeklies)
- [ ] Render diff tracking (R-labels, pins for identical re-renders)
- [ ] Undo (`belam -z`) — session-scoped inverse diff stack, cascade-aware, returns F⏪ signal
- [ ] CLI wiring (replace default `belam` handler)

### V2 Features (fast-follow)

- [ ] Dry-run on create (`--dry`)
- [ ] Boot hook integration (auto-run `belam` at session start → R0)
- [ ] Filter flags for memory (`--tag`, `--since`)

## Subagent Work Breakdown

1. **Core Engine** — `scripts/codex_engine.py`: namespace resolution, primitive loading, supermap renderer, zoom renderer, field indexer, memory boot section, render diff tracker
2. **Mutation Paths** — edit/create modes: field-indexed writes, cascading consequences, bidirectional edges, type validation, diff-on-mutation output
3. **Action & Graph** — execute mode (wrapping existing scripts), graph view renderer, path-between-nodes
4. **Integration** — CLI wiring into `belam_cli.py`, replace default handler, testing, polish

## Acceptance Criteria

- [ ] `belam` with no args renders compact supermap with all primitive types
- [ ] `belam p1` shows field-indexed pipeline view
- [ ] `belam -e t3 3 'high'` edits priority and returns diff
- [ ] `belam -g d2` renders local subgraph
- [ ] `belam -x p1 run` executes pipeline experiment
- [ ] `belam -n t 'New task'` scaffolds and indexes
- [ ] Memory boot section shows 5 today + 3 dailies + 3 weeklies
- [ ] Status edits trigger downstream unblock checks
- [ ] All existing belam commands still work as sugar over `-x`

## Notes

- Design conversation with Shael: 2026-03-20 16:19-17:55 UTC
- Key design principle: clock cycles over tokens — all rendering is deterministic Python, zero LLM reasoning
- Engine reads primitives and calls existing scripts — doesn't replace them
- Filesystem is source of truth, engine is the lens
- Render diffs are ephemeral (session-scoped, in-memory only)
