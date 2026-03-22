---
primitive: task
status: open
priority: high
created: 2026-03-22
owner: belam
depends_on: [codex-engine-v3-temporal-mcp-autoclave]
upstream: [codex-engine-v3]
downstream: [build-codex-layer-v1]
tags: [codex-engine, legendary-map, v3-phase3, attention-architecture]
pipeline: codex-engine-v3
phase: 3
---

# Codex Engine V3 Phase 3: Legendary Map

## Description

Add a `lm` (legendary map) namespace to the supermap that renders the engine's own action grammar as navigable coordinates. The LM is not documentation *about* the engine — it IS a namespace on the engine. This creates a recursive self-referential attention pattern: the agent sees coordinates that describe how to use coordinates, and modifying the engine automatically updates the LM.

### Core Insight

The supermap shows **what exists** (state). The legendary map shows **what you can do** (actions). Both live in the same coordinate space, processed in a single attention pass. The LLM forms cross-attention between action patterns (`lm3`) and targets (`p3`) — they're not separate instruction sets, they're one unified structure.

### Example: Combined Supermap with Expanded LM

```
╶─ Codex Engine Supermap [2026-03-22 21:00 UTC]
╶─ lm  legendary map (actions & workflows)
│  ╶─ lm1   navigate        {coord}              → render primitive
│  ╶─ lm2   edit-field       e1{coord} {f} {v}    → set field on primitive
│  ╶─ lm3   edit-body        e1{coord} B+ {text}  → append to body
│  ╶─ lm4   create           e2 {ns} "title"      → new primitive in namespace
│  ╶─ lm5   extend-ns        e3 {ns}.{sub}        → register new namespace
│  ╶─ lm6   orchestrate      e0                   → full pipeline sweep
│  ╶─ lm7   pipeline-kick    e0p{n}               → advance pipeline
│  ╶─ lm8   filter-tag       {coord} --tag {t}    → filter by tag
│  ╶─ lm9   filter-since     {coord} --since {d}  → filter by date
│  ╶─ lm10  persona-view     {coord} --as {role}  → persona-filtered view
│  ╶─ lm11  graph            {coord} -g           → show relationships
│  ╶─ lm12  diff             .d                   → diff since anchor
│  ╶─ lm13  anchor           .a                   → reset diff anchor
│  ╶─ lm14  pipeline-launch  belam pipeline launch {ver} --desc "..." --kickoff
│  ╶─ lm15  pipeline-status  belam pipeline {ver}  → show pipeline state
│  ╶─ lm16  memory-search    memory_search("{q}")  → search memory entries
╶─ p   pipelines (6)
│  ╶─ p1    codex-engine-v2-modes  phase1_complete/high
│  ╶─ p2    codex-engine-v3  archived/medium
│  ...
╶─ t   tasks (16)
│  ╶─ t1    build-incremental-relationship-mapper  active/medium
│  ...
╶─ e   modes (4)
│  ╶─ e0    orchestrate
│  ╶─ e1    edit
│  ╶─ e2    create
│  ╶─ e3    extend
╶─ i   personas (3)
│  ╶─ i1    architect
│  ╶─ i2    builder
│  ╶─ i3    critic
╶─ m   memory
│  ...
```

### Key: LM is auto-generated, not hand-maintained

The renderer reads:
- `modes/*.md` → e0–e3 action patterns (lm1–lm6)
- `commands/*.md` → CLI workflows (lm14–lm15)
- Engine capabilities (flags, filters) → lm8–lm10
- Render engine verbs → lm12–lm13
- Tool integrations (memory_search, etc.) → lm16+

When a new mode is added via `e3`, the LM auto-expands. When a command is archived, its LM entry disappears. The lathe sees itself.

### Recursive Self-Observation Property

The LM describes how to modify the supermap. The supermap contains the LM. Modifying the engine (e3 adds a namespace) changes what the LM renders, which changes what the agent sees, which changes how the agent uses the engine. This creates a feedback loop through the attention mechanism:

```
Agent reads LM → uses coordinates → modifies primitives → 
supermap re-renders → LM updates → agent reads updated LM → ...
```

This is novel because it places the action space *inside* the state space the model attends over, rather than in a separate system prompt instruction block. The model doesn't switch between "reading instructions" and "reading state" — it processes them as one relational structure.

### Implementation

1. **LM Renderer** (~150-250 lines in `codex_engine.py` or new `codex_legend_renderer.py`)
   - Scans modes/, commands/, engine flags, render verbs
   - Generates `lm` namespace entries with coordinate, name, syntax pattern
   - Renders in same dense format as other supermap namespaces
   - Inserted as first namespace in supermap output (top-of-tree priming)

2. **Supermap Integration**
   - `lm` namespace renders before `p`, `t`, `d` etc.
   - Full expansion by default (unlike other namespaces which truncate at 5)
   - Each entry shows: coord, verb name, syntax pattern, brief description

3. **Auto-update hooks**
   - `e3` (extend mode) triggers LM re-render
   - `e2` in modes/ or commands/ namespace triggers LM re-render
   - Materializer picks up changes via inotify

### Acceptance Criteria

- [ ] `lm` namespace appears in supermap output
- [ ] All engine modes (e0–e3) have corresponding `lm` entries
- [ ] All active commands have `lm` entries with syntax patterns
- [ ] Render engine verbs (`.d`, `.a`, etc.) have `lm` entries
- [ ] Adding a mode via `e3` auto-generates new `lm` entry on next render
- [ ] Archiving a command removes its `lm` entry
- [ ] LM renders fully expanded (no truncation)
- [ ] Total LM payload ≤ 1KB for current action set
- [ ] Agent can use `lm{n}` coordinates to navigate to action descriptions

## Open Questions

1. Should the LM also include tool-call patterns (memory_search, sessions_spawn) or only codex-native operations?
2. Should `lm` entries be navigable (`lm3` shows full syntax + examples) or display-only?
3. Workflow compositions — should multi-step patterns get their own `lm` entries? (e.g., "pipeline lifecycle: e2 p → e0p{n} → e1p{n} status archived")
