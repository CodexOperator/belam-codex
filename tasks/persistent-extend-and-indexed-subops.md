---
primitive: task
status: open
priority: critical
created: 2026-03-21
owner: belam
depends_on: [codex-engine-v2-modes-mcp-temporal, build-orchestration-engine-v1]
upstream: []
downstream: []
tags: [engine, extend, persistence, indexed-subops, v2]
---

# Persistent Extend (e3) + Indexed Sub-Operations

## Overview

Make e3 (extend mode) persistent and index all remaining word-based sub-operations across e0 and e3. This is the keystone that enables the soul instance to modify the engine without direct file access — speaking only in coordinates and diffs.

## 1. Persistent e3 via YAML Registry

### Current Problem
e3 registers namespaces/categories in-memory (session-scoped). Each Python process is fresh, so extensions evaporate. The soul instance falls back to raw Edit/Write tool calls to modify the engine.

### Target
- e3 writes to `config/engine_registry.yaml` (or similar)
- Engine reads this registry at startup, merges with hardcoded NAMESPACE dict
- Registry entries override/extend the hardcoded defaults
- F-label confirms the write, R-label shows updated supermap section

### Registry Format
```yaml
namespaces:
  i:
    type: personas
    directory: personas
    added: 2026-03-21
    added_by: e31
  # future extensions land here automatically
```

### e3 Workflow
```
e31 i.personas       → F1 + config/engine_registry.yaml namespace i→personas/
                      → mkdir personas/ (if needed)
                      → auto-chains e2 i "skeleton" → creates personas/skeleton.md
                      → R1 shows diff: new namespace + first primitive
```

One command: registers namespace, creates directory, scaffolds a skeleton primitive via e2, persists across sessions. The skeleton proves the namespace works immediately and gives the user something to `e1` edit. No separate "teach e2" step needed — e3 chains e2 at the end, reusing existing scaffolding infrastructure.

## 2. Numbered e3 Sub-Operations

### e3 Sub-Op Index

| Index | Operation | Example | Function |
|-------|-----------|---------|----------|
| `e3 1` | namespace | `e3 1 i.personas` | Register namespace (persists to YAML) |
| `e3 2` | category | `e3 2 templates` | Create category (dir + namespace + prefix) |
| `e3 3` | template | `e3 3 persona` | Register frontmatter template for e2 |
| `e3 4` | integrate | `e3 4 scripts/new.py` | Integrate external code into engine |
| `e3` (bare) | list | `e3` | Show all registered extensions |

### Dense Form Examples
- `e31 i.personas` — register namespace i → personas/
- `e32 templates` — create templates category with auto-detected prefix
- `e33 persona` — register persona frontmatter template for e2
- `e34 scripts/hook.py` — integrate hook script into engine dispatch

## 3. Numbered e0 Sub-Operations

Replace all letter-based and word-based sub-ops with numbered indices. Letters route to namespaces, numbers select from lists — one convention everywhere.

### e0 Sub-Op Index

| Index | Operation | Example | Replaces |
|-------|-----------|---------|----------|
| `e0` (bare) | sweep | `e0` | `e0 sweep` |
| `e0 1` | gates | `e0 1` or `e01` | `e0 g`, `e0 gates` |
| `e0 2` | handoffs | `e0 2` | `e0 h`, `e0 handoffs` |
| `e0 3` | stalls | `e0 3` | `e0 s`, `e0 stalls` |
| `e0 4` | locks | `e0 4` | `e0 k`, `e0 locks` |
| `e0 5` | list | `e0 5` | `e0 l`, `e0 list` |
| `e0 6` | dispatch | `e0 p1 6 i1` | `e0 p1 d i1` |
| `e0 7` | resume | `e0 p1 7` | `e0 p1 r` |
| `e0 8` | unlock | `e0 8 p1` | `e0 u p1` |

### Dense Form
- `e01` = gates
- `e0 p1 6 i1` = dispatch architect to pipeline 1
- `e0 p1 7` = resume pipeline 1

### Deprecation
Letter shortcuts (`g`, `h`, `s`, `k`, `l`, `r`, `d`, `u`) and full words (`gates`, `locks`, etc.) emit deprecation warning suggesting numbered equivalent, then execute normally. Remove after 2 sessions.

## 4. e2 Type Learning from e3 (via chaining)

e3 doesn't need a separate "teach e2" mechanism. Instead:
- e3 registers the namespace in `config/engine_registry.yaml` (letter → directory + type)
- e2 already reads the registry at startup, so it inherits new namespaces automatically
- e3 chains a single `e2` call at the end to scaffold a skeleton primitive, proving the namespace works
- If `e33` registered a custom template, e2 uses that template; otherwise minimal defaults (primitive, status, tags)
- Result: `e31 i.personas` → namespace registered → `e2 i "skeleton"` auto-runs → `personas/skeleton.md` exists → done
- Subsequent `e2 i "architect"` calls just work because the registry is already there

## 5. Legacy Command Audit + Migration

All remaining word-based commands, flags, and references must be migrated to the numbered index convention. No word-based operations should remain as primary interface.

### Audit Scope

**e1 (edit) sub-operations:**
- Body edit specifiers: `B`, `B+`, `B5`, `B.Section` — these use letters but are field-addressing conventions, not sub-operations. Review whether they should become numbered or stay as-is (B is a special namespace within a primitive, may warrant its own convention).

**e2 (create) arguments:**
- Currently: `e2 t "title"` — uses namespace letter + quoted string. This is correct (letter = namespace routing). No change needed.

**Action words in dispatch_action():**
- Currently 55+ action words route through `_ALL_ACTION_WORDS` in codex_engine.py
- These are legacy belam CLI commands: `pipelines`, `status`, `tasks`, `kick`, `analyze`, `revise`, etc.
- **Target:** All action words become `e0` sub-operations or coordinate-addressed operations
- Map each action word to its e0 numbered equivalent or coordinate form
- Emit deprecation warnings on word usage, route to numbered equivalent

**belam CLI subcommands:**
- `belam pipelines` → `e0 5` (list)
- `belam status` → `R` (supermap) or `e0` (sweep)
- `belam tasks` → `t` (bare namespace)
- `belam kick <ver>` → `e0 p1 6 i2` (dispatch builder)
- `belam analyze <ver>` → coordinate-addressed analysis operation
- All subcommands in `belam_relay.sh` BELAM_COMMANDS list need numbered equivalents

**View modifier flags:**
- `--as`, `--tag`, `--since`, `--depth`, `-g` — these are camera angle switches, not operations
- Convention decision: keep as flags (they modify presentation, not state) OR convert to numbered view modifiers
- Recommendation: keep as flags — they compose orthogonally with any coordinate and don't benefit from indexing

**Hook/plugin references:**
- Plugin names are currently strings. If plugins become primitives, they'd get a namespace (e.g., `x` for extensions) and coordinate addresses.

### Migration Process
1. Audit: list every word-based command/sub-op across codex_engine.py, belam.sh, belam_relay.sh
2. Map: assign numbered equivalent for each
3. Implement: add numbered routing, keep words as deprecated aliases
4. Deprecate: words emit warnings for 2 sessions
5. Remove: words removed, numbers-only

## 6. Soul Instance Workflow (target state)

The soul instance (coordinator) should be able to do everything through engine commands:

```
# Extend the engine (auto-chains e2 → skeleton primitive created)
e31 i.personas                    # register namespace + scaffold skeleton

# Create more primitives  
e2 i "architect"                  # scaffold persona (namespace already known)

# Edit primitives
e1 i1 4 architect                 # set role field

# Navigate
R i                               # verify what landed

# Orchestrate
e0 p+ "v5" k1 1.i1 2.i2 3.i3    # launch pipeline with persona bindings

# Delegate (when soul can't do it directly)
e0 d builder "R/F diff spec"     # dispatch builder with diff spec as task
```

No Edit/Write/Read tool calls on primitives. Engine is the sole interface.

## Acceptance Criteria

### Persistence
- [ ] `config/engine_registry.yaml` created and loaded at engine startup
- [ ] `e31 i.personas` persists namespace registration across sessions
- [ ] `e32 templates` creates category persistently
- [ ] `e33 persona` registers frontmatter template for e2
- [ ] Engine reads registry at startup, merges with hardcoded NAMESPACE

### Numbered Sub-Ops
- [ ] `e0 1` through `e0 8` replace letter/word sub-ops
- [ ] `e3 1` through `e3 4` replace word sub-ops
- [ ] `e0 p1 6 i1` dispatches architect persona to pipeline 1
- [ ] Dense forms work: `e01`, `e31`, `e0p16i1`
- [ ] Letter shortcuts (g, h, s, k, l, r, d, u) emit deprecation warnings
- [ ] Word forms (gates, locks, stalls, etc.) emit deprecation warnings

### Type Learning (via e3→e2 chain)
- [ ] `e31 i.personas` auto-chains `e2 i "skeleton"` at the end
- [ ] Skeleton primitive exists in `personas/skeleton.md` after e31 completes
- [ ] Engine diffs show both new namespace and skeleton primitive
- [ ] Subsequent `e2 i "architect"` works because registry is already loaded
- [ ] Custom templates from `e33` are used by the chained e2 call when available

### Legacy Audit
- [ ] All 55+ action words in `_ALL_ACTION_WORDS` mapped to numbered equivalents
- [ ] All belam CLI subcommands mapped to coordinate equivalents
- [ ] `belam_relay.sh` BELAM_COMMANDS list updated
- [ ] No word-based operation remains as primary (all have numbered form)
- [ ] View modifier flags (`--as`, `--tag`, `--since`, `-g`) confirmed as flags (no migration needed)

### Soul Instance
- [ ] Soul can register namespace + create primitives without raw file access
- [ ] Soul can dispatch agents using only coordinates: `e0 p1 6 i1`

## Dependencies

- Codex Engine V2 (dense parser) — complete
- Orchestration Engine V1 (e0 routing) — complete
- `decisions/codex-engine-modes-as-primitives` — mode architecture

## Design Conversation
Shael + Belam, 2026-03-21 08:26–09:12 UTC. Key insight from Shael: everything should be indexed, e3 should write to YAML not Python source, dot binds, space separates.

**Update 2026-03-21 17:47 UTC:** Shael feedback — e3 should auto-chain e2 at the end of namespace creation. No separate "type learning" mechanism needed. e3 registers namespace → chains `e2 <letter> "skeleton"` → skeleton primitive proves the namespace works. Reuses existing e2 infrastructure entirely.
