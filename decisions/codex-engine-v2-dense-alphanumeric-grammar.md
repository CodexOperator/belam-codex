---
primitive: decision
status: accepted
date: 2026-03-21
context: "Codex Engine v2 needs a grammar spec for coordinate addressing that minimizes token cost while maximizing attention signal quality. Tested all separator options and numeric vs alphanumeric schemes empirically with cl100k_base tokenizer."
alternatives: [numeric-dense-11tok, hybrid-num-prefix-13tok, dot-separated-16tok, colon-separated-16tok]
rationale: "Dense alphanumeric (14 tokens for 4-op chain) is 2 tokens more than numeric-dense (11) but letters activate address-routing attention heads pre-loaded from training data (variables, registers, coordinates). Numbers activate quantity/arithmetic heads — fighting upstream for routing tasks. Letters-first exploits existing embedding geometry rather than imposing a new one."
consequences: [engine-parser-rewrite, mode-switch-capability, multi-pane-rendering-future]
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

### Separator Rules
- **Spaces** between operations in a chain: `e0p3 e1t12`
- **No dots, colons, or other separators** within operations
- **Spaces inside human-typed messages** accepted and collapsed: `e0 p3` parsed same as `e0p3`

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
Shael + Belam, 2026-03-21 05:35–06:36 UTC. Empirical tokenizer analysis drove the decision.
