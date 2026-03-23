---
primitive: task
status: archived
priority: critical
created: 2026-03-22
archived: 2026-03-23
archive_reason: pipeline build-codex-layer-v1 archived
owner: belam
depends_on: [codex-layer-context-injection]
upstream: [codex-engine-v3-legendary-map]
downstream: []
tags: [codex-layer, v1, interceptor, output-codec, symbolic-dispatch, infrastructure]
pipeline: build-codex-layer-v1
supersedes: [codex-layer-output-codec, codex-layer-symbolic-dispatch]
---

# Codex Layer v1: Programmatic Coordinate Guardrails

## Description

The codex layer is a programmatic interception system that steers all workspace interaction through the codex engine's coordinate system. When an agent or human reaches for raw shell commands (`grep`, `echo`, `cat`, manual file read/write) where an engine coordinate already exists, the layer intercepts and redirects.

This is the **general form** of what the output-codec and symbolic-dispatch tasks were circling around. Those tasks are rolled into this one as delivery phases.

### Core Architecture

```
Agent/Human input
       │
       ▼
┌─────────────────┐
│  Codex Layer    │  ← reads Legendary Map (lm namespace)
│  Interceptor    │     to know what coordinates exist
├─────────────────┤
│ 1. Pattern match raw commands against known engine equivalents
│ 2. If match: redirect → "Use e1t5 status open" 
│ 3. If no match: passthrough to shell
│ 4. All outputs → codec → transient coordinates
└─────────────────┘
       │
       ▼
  Codex-formatted response
  with addressable coordinates
```

### What makes this the general form

The output-codec (transient result registers) and symbolic-dispatch (prefix grammar) are both instances of the same pattern: **every interaction with the workspace should go through coordinates, and the layer enforces this programmatically.** Breaking it into separate tasks missed the unified architecture:

- **Interceptor** = symbolic-dispatch generalized (not just prefix routing, but also catching `grep status tasks/*.md` → `e0t --filter status:open`)
- **Output codec** = the response side of the same pipe (everything comes back coordinate-addressed)
- **Guardrails** = the novel piece — the layer actively redirects away from raw commands using the LM as its knowledge base

### Relationship to Legendary Map

The LM tells the agent what coordinates exist. The codex layer *enforces* their use. Together they create a closed loop:

1. LM primes attention toward coordinate patterns
2. Agent uses coordinates (or tries raw commands)
3. Codex layer intercepts raw commands → redirects to coordinates
4. Output comes back codex-formatted with transient coords
5. Next turn: LM + result register are both in context

The layer reads the LM programmatically to build its interception rules. When the engine adds new capabilities (via `e3`), the LM updates, and the interceptor auto-learns the new patterns. No manual rule maintenance.

## Delivery Phases

### Phase A: Output Codec (from codex-layer-output-codec)

Extend `codex_codec.py` to handle command outputs:

1. `output_to_codex(command, stdout, stderr, returncode)` — recognize patterns:
   - JSON objects/arrays → field-addressed codex
   - Tabular output → row-addressed codex
   - Key-value pairs → field-addressed codex
   - Known scripts (orchestration_engine, launch_pipeline, git) → specific parsers
   - Unstructured text → passthrough with coord wrapper

2. Result register — transient coordinates for command outputs:
   ```
   orchestration_engine.py → _ = {p1:phase1_complete, p2:archived, ...}
   _.p1.status → "phase1_complete"
   _.p1 > e1    → "open p1 in edit mode"
   _1, _2, _3   → previous results (stack)
   ```

3. Dot-notation field access into result fields

### Phase B: Symbolic Dispatch (from codex-layer-symbolic-dispatch)

Wire dispatch grammar through the render engine:

```
Bare coords  → codex engine    (e0, t5, e1t5)
Prefix .     → render verbs    (.d diff, .a anchor, .s status)
Prefix !     → shell pass      (!git status)
Pipe >       → output routing  (e0 > t5, !cmd > .d)
```

1. Dispatch parser — route by prefix
2. UDS dispatch — send command, get codex response
3. Pipe semantics — result register → next command context
4. All responses through output codec

### Phase C: Interceptor / Guardrails (the new piece)

The layer that catches raw commands and redirects to coordinates:

1. **Pattern library** — built from LM namespace:
   - `grep -l "status: open" tasks/*.md` → `e0t --filter status:open`
   - `cat tasks/foo.md` → `t{n}` (resolve slug → coord)
   - `echo "..." >> tasks/foo.md` → `e1t{n} B+ "..."`
   - `python3 scripts/orchestration_engine.py` → `e0`
   - `Read file_path=tasks/...` → `t{n}` (tool call interception)

2. **Interception mechanism** — either:
   - `before_exec` hook in OpenClaw (if available)
   - Wrapper in render engine that the agent calls instead of `exec`
   - Response annotation: let command run but append "💡 Next time: use `e1t5 status open`"

3. **Auto-update from LM** — interceptor reads `lm` namespace entries to build pattern→coordinate mappings. New engine capabilities auto-generate new interception rules.

4. **Graduated enforcement**:
   - Phase 1: advisory ("💡 Coordinate equivalent: ...")
   - Phase 2: redirect with confirmation ("Redirecting to e1t5...")
   - Phase 3: block with override ("Raw command blocked. Use e1t5 or prefix with ! to force.")

## Acceptance Criteria

### Phase A (Output Codec)
- [ ] `output_to_codex()` handles JSON, tabular, key-value, raw text
- [ ] Known script outputs have specific parsers
- [ ] Transient coordinates assigned (_ latest, _N history)
- [ ] Dot notation field access works
- [ ] Token savings measured vs raw output

### Phase B (Symbolic Dispatch)
- [ ] Bare coordinates dispatch through codex engine
- [ ] `.` prefix dispatches render verbs
- [ ] `!` prefix passes through to shell
- [ ] Pipe `>` chains output to next command
- [ ] All outputs through codec

### Phase C (Interceptor)
- [ ] Pattern library covers top-10 most common raw commands
- [ ] Patterns auto-generated from LM namespace
- [ ] Advisory mode works (suggest coordinates without blocking)
- [ ] Redirect mode works (execute coordinate equivalent)
- [ ] Adding new LM entry auto-creates new interception rule
- [ ] Works for both exec tool calls and human CLI input

## Notes

Supersedes `codex-layer-output-codec` and `codex-layer-symbolic-dispatch` — those tasks are now Phase A and Phase B of this unified task. The context-injection task remains separate as it's already in-pipeline and is a prerequisite (the hook infrastructure this layer builds on).
