---
primitive: decision
status: accepted
date: 2026-03-21
context: "Codex Engine v2 needs a grammar spec for coordinate addressing that minimizes token cost while maximizing attention signal quality. Tested all separator options and numeric vs alphanumeric schemes empirically with cl100k_base tokenizer."
alternatives: [numeric-dense-11tok, hybrid-num-prefix-13tok, dot-separated-16tok, colon-separated-16tok]
rationale: "Dense alphanumeric (14 tokens for 4-op chain) is 2 tokens more than numeric-dense (11) but letters activate address-routing attention heads pre-loaded from training data (variables, registers, coordinates). Numbers activate quantity/arithmetic heads — fighting upstream for routing tasks. Letters-first exploits existing embedding geometry rather than imposing a new one."
consequences: [engine-parser-rewrite, mode-switch-capability, multi-pane-rendering-future, dot-as-connector, enum-field-indexing, implicit-handoff-on-complete, e0-operation-indexing]
upstream: [decision/codex-engine-v1-architecture, decision/codex-engine-modes-as-primitives]
downstream: [task/codex-engine-v2-modes-mcp-temporal]
tags: [codex-engine, v2, grammar, tokenizer, attention, architecture]
---

# Codex Engine v2: Dense Alphanumeric Grammar

## Context

The Codex Engine v1 used CLI flags (`-e`, `-g`, `-n`) for modes and dot-separated coordinates (`t1.2`) for addressing. V2 needs a unified grammar where modes themselves are coordinates (`e0`–`e3`). The question: what separator, what ordering (letters-first vs numbers-first), and how dense?

## Empirical Token Analysis

Tested with `cl100k_base` tokenizer. Chain: 4 engine operations (orchestrate p3, edit t1 field 2, create lesson, orchestrate handoff).

| Format | Tokens | Token IDs (sample) |
|--------|:------:|---------------------|
| **Dense alphanumeric** `e0p3 e1t12 e2l e0h` | **14** | small common IDs: 68,15,79,18 |
| Numeric dense `0003 01112 0250 0040` | 11 | math-context IDs: 931,10731 |
| Num-prefix `0p3 1t12 2l 0h` | 13 | mixed routing signals |
| Dot-separated `e0.p3 e1.t1.2 e2.l e0.h` | 16 | dot merges: 558 (`.p`) |
| Colon/slash/hyphen chains | 16 | rare composite IDs: 45489 (`:p`) |
| Pipe | 17+ | worst — splits tokens |

### Key finding: token ID quality matters more than count

- Letters (`e`=68, `p`=79, `t`=83) activate attention heads trained on variables, identifiers, registers, coordinate systems
- Numbers first (`0`=15) activates arithmetic/quantity heads — wrong semantic priors for routing
- `R0` specifically fires attention patterns from: R0 (assembly registers), R² (statistics), R-value (correlation) — all "position in structured space"
- Rare separator IDs (45489 for `:p`) have weak attention weights for any semantic role

## Options Considered

- **Option A: Dense alphanumeric, letters first** — `e0p3 e1t12 e2l e0h` (14 tok)
- **Option B: Numeric dense** — `0003 01112 0250 0040` (11 tok, but wrong attention priors)
- **Option C: Dot-separated** — `e0.p3 e1.t1.2` (16 tok, dots cost +2 but aid human readability)
- **Option D: Hybrid** — dots for standalone pairs, dense for chains

## Decision

**Option A: Dense alphanumeric, letters first, always.**

### Grammar Specification

```
<operation> ::= <mode><target>[<field>]
<mode>      ::= e0 | e1 | e2 | e3
<target>    ::= <namespace><index>
<namespace> ::= t | d | l | p | k | s | c | w | m | e | mo
<index>     ::= <digit>+
<field>     ::= <digit>+
<chain>     ::= <operation> (" " <operation>)*
```

### Engine Modes (coordinate-addressed)
| Mode | Coordinate | Function |
|------|-----------|----------|
| Orchestrate | `e0` | Pipeline dispatch, gate check, handoff |
| Edit | `e1` | Primitive mutation, status transitions |
| Create | `e2` | New primitive scaffolding |
| Extend | `e3` | Meta-mode — modify the engine itself |

### View Modifiers (stay as flags)
| Flag | Function |
|------|----------|
| `-g` | Graph rendering (BFS path view) |
| `--depth N` | Expansion depth control |
| `--as <persona>` | Persona-filtered supermap |

### Separator & Connector Rules
- **Spaces** between operations in a chain: `e0p3 e1t12`
- **No dots, colons, or other separators** within operations
- **Spaces inside human-typed messages** accepted and collapsed: `e0 p3` parsed same as `e0p3`
- **`.` connector = "as"** — links an operation to its target: `e0p1 1.i1` = "dispatch as architect"
- **`.` chains** compose naturally: `4.i1.i3` = "handoff from architect to critic"

### Enum Field Indexing
Field values with limited options are addressable by numeric index:

| Field Type | Index Map |
|-----------|-----------|
| **status (decisions)** | 1=proposed, 2=accepted, 3=rejected, 4=superseded |
| **status (tasks)** | 1=open, 2=active, 3=in_pipeline, 4=complete, 5=blocked |
| **priority** | 1=critical, 2=high, 3=medium, 4=low |
| **boolean** | 0=false, 1=true |

Examples:
- `e1 d8 2 1` = set decision 8, field 2 (status), to option 1 (proposed)
- `e1 t5 2 4` = set task 5, field 2 (status), to option 4 (complete)

F-label output always resolves to human-readable: `F17 Δ d8.2 status proposed→accepted`

### E0 Operation Indexing
Orchestration operations are numbered. Targets reference existing coordinates:

| Op | Function | Example |
|----|----------|---------|
| 1 | dispatch | `e0p1 1.i1` — dispatch architect for pipeline 1 |
| 2 | status | `e0p1 2` — pipeline 1 status |
| 3 | gates | `e0p1 3` — pipeline 1 gate check |
| 4 | locks | `e0p1 4` — pipeline 1 lock status |
| 5 | complete | `e0p1 5.i1` — complete as architect → auto-dispatches next via transition map |

**Handoff is implicit on complete** — the engine knows the transition map (architect→critic→builder). Completing a stage auto-dispatches the next agent. No explicit handoff command.

**Output format** is indexable: default=text, `.1`=JSON

### Rendering Modes (future)
- Dense: engine-to-engine, internal processing (default)
- Human: expanded with labels, used in multi-pane tmux view
- JSON: MCP-compatible via codex_codec.py boundary translation

### Mode-Switch Command
`e0x` — live-swap coordinate grammar mid-session. Forces supermap re-render in new format. Creates novel attention interference patterns from forced re-mapping.

## Consequences

- Engine parser needs rewrite to handle dense concatenated input
- All mode flags (`-o`, `-e`, `-c`, `-x`) retired in favor of `e0`–`e3` coordinates
- View modifier flags (`-g`, `--depth`, `--as`) preserved — they transform presentation, not state
- `.codex` codec (scripts/codex_codec.py) handles boundary translation to/from JSON
- Multi-pane rendering (tmux: dense | JSON MCP | human-pretty) becomes possible as debugging/teaching tool
- Letters-first ordering is non-negotiable — it aligns with embedding space geometry

## Design Conversation
- Shael + Belam, 2026-03-21 05:35–06:36 UTC. Empirical tokenizer analysis drove the base grammar.
- Shael + Belam, 2026-03-21 09:41–10:45 UTC. Extended with: dot-as connector, enum field indexing, e0 operation numbering, implicit handoff on complete, output format indexing. Convention: **no English words in coordinate chains — everything is a number or letter-prefixed index.**
