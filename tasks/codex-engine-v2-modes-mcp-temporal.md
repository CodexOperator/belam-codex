---
primitive: task
status: archived
priority: high
project: multi-agent-infrastructure
depends_on: []
tags: [engine, codex, modes, grammar, v2]
created: 2026-03-21
archived: 2026-03-22
archive_reason: status: complete
---

# Codex Engine v2: Dense Alphanumeric Modes

## Overview

Rewrite the engine parser to support dense alphanumeric grammar (d10) and coordinate-addressed modes (e0–e3), replacing CLI flags with the uniform addressing system established in v1.

## Design Principles

1. **Everything is a primitive** — modes, commands, extensions, even the engine's own config
2. **Same pattern everywhere** — coordinates, frontmatter, R-label diffs, .codex serialization
3. **The lathe builds the lathe** — extend mode (e3) uses primitives to modify the primitive set
4. **Token efficiency is non-negotiable** — dense alphanumeric, letters first (d10)

---

## 1. Dense Alphanumeric Parser

### Grammar (from d10)

```
<operation> ::= <mode><target>[<field>]
<mode>      ::= e0 | e1 | e2 | e3
<target>    ::= <namespace><index>
<namespace> ::= t | d | l | p | k | s | c | w | m | e | mo
<index>     ::= <digit>+
<field>     ::= <digit>+
<chain>     ::= <operation> (" " <operation>)*
```

### Input Examples
- `e0p3` — orchestrate pipeline 3
- `e1t12` — edit task 1 field 2
- `e2l` — create lesson
- `e0p3 e1t12 e2l e0h` — chained: 4 operations, 14 tokens
- `e0 p3` — spaced input accepted, collapsed to `e0p3`

### Parser Requirements
- Detect `eN` prefix as mode switch in a chain
- Accept both dense (`e0p3`) and spaced (`e0 p3`) input
- View modifiers (`-g`, `--depth`, `--as`) remain as flags — they compose orthogonally

---

## 2. Modes as Coordinates

### Current → Target

| Current Flag | New Coordinate | Function |
|-------------|---------------|----------|
| **`R -o` | `e0` | Orchestrate — pipeline dispatch, gate check, handoff |
| **`R -e` | `e1` | Edit — primitive mutation, status transitions |
| **`R -n` | `e2` | Create — new primitive scaffolding |
| **`R -x` | `e3` | Extend — meta-mode, modify the engine itself |
| (implicit) | bare coords | View — current default, unchanged |

### Mode Primitives
- Modes stored in `modes/*.md` with frontmatter defining behavior spec
- Namespace prefix: `e` → resolves to `modes/` directory (same prefix as mode coordinates)
- `e` chosen as natural embedding-space entry point — most common English letter, anchors meaning-mapping
- Each mode primitive declares: applicable namespaces, transformations, composability
- `R0.e` views engine modes section in supermap; `e` bare lists all modes
- Composable: `e0p3 -g` = orchestrate pipeline 3, show result as graph

---

## 3. Extend Mode (e3) — The Meta-Layer

### Purpose
Use the engine to modify the engine.

### Operations
- `e3 category <name>` → create new primitive category with namespace prefix
- `e3 namespace <prefix> <type> <dir>` → register new namespace in engine
- `e3 integrate <path>` → integrate external code/plugin into engine resolution
- `e3 template <type>` → create frontmatter template for new primitive type

### Self-Documentation
Each extend operation creates a primitive trail — `e3` to see all extensions applied.

---

## 4. Retire Legacy Flags

- Remove `-o`, `-e`, `-c`, `-x` flag parsing from `codex_engine.py`
- Preserve `-g`, `--depth`, `--as`, `--tag`, `--since` as view modifiers
- Update `R help` / action word registry for new grammar
- Backward compatibility period: warn on old flags, suggest coordinate equivalent

---

## 5. RAM State Layer (dulwich)

### Architecture
- `dulwich` pure-Python git library for in-memory state tree
- `/dev/shm/belam-ephemeral/` or pure in-memory bare repo
- Ephemeral state lives only during session/pipeline run
- Disk writes only on explicit checkpoint or session end
- Supermap hook reads from RAM tree instead of scanning disk

### Benefits
- Branching (speculative state)
- Diffing (what changed between operations)
- Merging (reconcile parallel agent work)
- Rollback without undo stack

---

## Acceptance Criteria

- [ ] Dense parser handles chained operations (`e0p3 e1t12 e2l e0h`)
- [ ] Spaced input collapsed correctly (`e0 p3` → `e0p3`)
- [ ] Modes e0–e3 functional, replacing flags
- [ ] Mode primitives in `modes/` directory with namespace `e`
- [ ] e3 extend creates primitive trail
- [ ] Legacy flags emit deprecation warning
- [ ] View modifiers compose with mode coordinates
- [ ] dulwich RAM tree prototype for ephemeral state
- [ ] codex_codec.py integrated as boundary layer

## Dependencies
- `decisions/codex-engine-v2-dense-alphanumeric-grammar.md` (d10) — grammar spec
- `decisions/codex-engine-v1-architecture.md` (d6) — foundation
- `research-openclaw-internals` pipeline — hook architecture findings

## Notes
- Pydantic for state validation: deterministic serialization → idempotent operations
- "Using the lathe to build a better lathe" — e3 is the meta-primitive that makes the system self-evolving
