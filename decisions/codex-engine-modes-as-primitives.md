---
primitive: decision
status: accepted
date: 2026-03-21
context: "Codex Engine V1 used CLI flags (-e, -g, -n, -x) for modes. These are invisible to the coordinate system — you can't address, compose, or extend them through primitives. Modes should be first-class citizens in the same addressing scheme as everything else."
alternatives: [flags-with-aliases, mode-as-namespace-prefix, mode-as-primitive]
rationale: "If everything is a primitive, modes must be too. Primitives are addressable, documentable, extensible. Flags are none of those things. Making modes primitives means e3 (extend) can create new modes — the lathe builds the lathe."
consequences: [modes-directory-created, mo-namespace-registered, e0-e3-replace-flags, extend-mode-creates-primitive-trail]
upstream: [decision/codex-engine-v1-architecture, decision/codex-engine-v2-dense-alphanumeric-grammar]
downstream: [task/codex-engine-v2-modes-mcp-temporal, task/build-orchestration-engine-v1]
tags: [codex-engine, v2, modes, primitives, architecture]
---

# Codex Engine: Modes as Primitives

## Context

V1 used CLI flags for modes: `-e` edit, `-g` graph, `-n` create, `-x` execute. These work but exist outside the coordinate system. You can't address a mode, query its spec, compose it with other primitives, or use the engine to extend the engine. Modes were second-class citizens in a system designed around first-class primitives.

## Options Considered

- **Option A: Flags with aliases** — Keep `-e`/`-g`/`-n`/`-x`, add short aliases. Simple but modes stay invisible to the primitive graph.
- **Option B: Mode as namespace prefix** — `edit/t1`, `graph/d2`. Modes become path segments. Addressable but creates a parallel hierarchy.
- **Option C: Modes as primitives** — Store mode specs in `modes/*.md` with `mo` namespace prefix. Modes are coordinates (`e0`–`e3`), stored as primitives with frontmatter defining behavior, applicable namespaces, and composability rules. Extend mode (`e3`) can create new modes.

## Decision

**Option C: Modes as primitives.**

### Mode Primitives

Each mode lives in `modes/` with frontmatter defining:
- **applicable_namespaces** — which primitive types this mode can operate on
- **transformations** — what state changes this mode produces
- **composability** — how this mode combines with view modifiers and other modes

| Coordinate | Mode | Function | Primitive |
|-----------|------|----------|-----------|
| `e0` | Orchestrate | Pipeline dispatch, gate check, handoff | `modes/orchestrate.md` |
| `e1` | Edit | Primitive mutation, status transitions | `modes/edit.md` |
| `e2` | Create | New primitive scaffolding | `modes/create.md` |
| `e3` | Extend | Meta-mode — modify the engine itself | `modes/extend.md` |

### Key Distinctions

**Plugins vs Commands (from same session):**
- **Plugins have presence** — they persist across turns, hook into lifecycle events, maintain state
- **Commands are fire-and-forget** — single invocation, stateless, return result
- These are *different primitive types* and shouldn't be collapsed

**Modes vs View Modifiers:**
- Modes change *what the engine does* (mutate state, spawn agents, create primitives)
- View modifiers change *how results are presented* (`-g` graph, `--depth`, `--as persona`)
- Modes are coordinates. View modifiers stay as flags. They compose orthogonally: `e0p3 -g`

### The Extend Meta-Layer (e3)

`e3` is what makes the system self-evolving:
- `e3 category <name>` → create new primitive category with namespace prefix
- `e3 namespace <prefix> <type> <dir>` → register new namespace in engine
- `e3 integrate <path>` → integrate external code/plugin into engine resolution
- `e3 template <type>` → create frontmatter template for new primitive type

Every `e3` operation creates a primitive trail — the engine's evolution is self-documenting.

## Consequences

- `modes/` directory created with `mo` namespace prefix
- CLI flags `-o`, `-e`, `-c`, `-x` retired in favor of `e0`–`e3`
- View modifiers (`-g`, `--depth`, `--as`) preserved — they compose with modes
- `e3` enables the engine to extend itself through primitives
- Mode specs are inspectable: `mo1` shows the orchestrate mode definition
- New modes can be added without code changes (primitive + engine registration)

## Design Conversation
Shael + Belam, 2026-03-21 04:03–05:01 UTC. Key insight from Shael: "modes should be primitives, not flags."
