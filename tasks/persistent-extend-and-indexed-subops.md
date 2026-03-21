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
                      → R1.i (new supermap section preview)
                      → e2 now knows how to scaffold 'i' primitives
```

One command: registers namespace, creates directory if needed, teaches e2 the new type, persists across sessions.

## 2. Indexed e3 Sub-Operations

### Current → Target

| Current | Indexed | Function |
|---------|---------|----------|
| `e3 namespace <prefix> <dir>` | `e31 <prefix>.<dir>` | Register namespace |
| `e3 category <name>` | `e32 <name>` | Create category (dir + namespace) |
| *(future)* `e3 template <type>` | `e33 <type>` | Register frontmatter template |
| *(future)* `e3 integrate <path>` | `e34 <path>` | Integrate external code |

### Dense Form Examples
- `e31 i.personas` — register namespace i → personas/
- `e32 templates` — create templates category with auto-detected prefix
- `e33 persona` — register persona frontmatter template for e2

## 3. Indexed e0 Sub-Operations (cleanup)

Current state: single-letter shortcuts exist (g, h, s, k, l, r, d, u) but full words also work. Remove word forms, single-letter only:

| Letter | Operation | Example |
|--------|-----------|---------|
| `g` | gates | `e0 g` or `e0g` |
| `h` | handoffs | `e0 h` |
| `s` | stalls | `e0 s` |
| `k` | locks | `e0 k` |
| `l` | list | `e0 l` |
| `r` | resume | `e0 p1 r` |
| `d` | dispatch | `e0 p1 d i1` |
| `u` | unlock | `e0 u p1` |

Full word forms (`gates`, `locks`, `stalls`, etc.) emit deprecation warning then route to single-letter equivalent.

## 4. e2 Type Learning from e3

When e3 registers a namespace, it also registers:
- The primitive type name (from the namespace type label)
- Default frontmatter fields for that type (from template if e33 was used, otherwise minimal: primitive, status, tags)
- e2 can then scaffold primitives of that type: `e2 i "new persona"` just works

## 5. Soul Instance Workflow (target state)

The soul instance (coordinator) should be able to do everything through engine commands:

```
# Extend the engine
e31 i.personas                    # register namespace

# Create primitives  
e2 i "architect"                  # scaffold persona

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

- [ ] `config/engine_registry.yaml` created and loaded at engine startup
- [ ] `e31 <prefix>.<dir>` persists namespace registration across sessions
- [ ] `e32 <name>` creates category (directory + namespace) persistently
- [ ] `e33 <type>` registers frontmatter template for e2
- [ ] e2 can scaffold new primitive types registered via e3
- [ ] e0 word sub-commands deprecated, single-letter is primary
- [ ] `e0 p1 d i1` dispatches architect persona to pipeline 1
- [ ] Engine reads registry at startup, merges with hardcoded NAMESPACE
- [ ] Soul instance can register namespace + create primitives without raw file access

## Dependencies

- Codex Engine V2 (dense parser) — complete
- Orchestration Engine V1 (e0 routing) — complete
- `decisions/codex-engine-modes-as-primitives` — mode architecture

## Design Conversation
Shael + Belam, 2026-03-21 08:26–09:12 UTC. Key insight from Shael: everything should be indexed, e3 should write to YAML not Python source, dot binds, space separates.
