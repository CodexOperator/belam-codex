---
primitive: task
status: open
priority: medium
created: 2026-03-21
owner: belam
depends_on: [codex-engine-v2-modes-mcp-temporal]
upstream: [decision/codex-engine-v2-dense-alphanumeric-grammar]
downstream: []
tags: [engine, codex, temporal, mcp, spacetimedb, v3]
---

# Codex Engine v3: Temporal State, MCP Native, Autoclave View

## Description

After v2 settles (dense grammar + coordinate modes), layer on the temporal database, MCP-native serving, and multi-agent shared views.

## 1. SpacetimeDB Temporal State Layer

- Evaluate SpacetimeDB vs SurrealDB vs EventStoreDB
- Pipeline state → temporal table with automatic diff generation
- Agent turns → temporal log (replaces JSONL conversation exports)
- Handoff records → temporal events with causal ordering
- `.codex` files as materialized views of temporal queries

## 2. Reactive .codex Materialization

- Agent action → write to SpacetimeDB
- Subscription fires → materialize updated `.codex` view
- `before_prompt_build` reads fresh `.codex` each turn
- Agent sees temporal diff in context — "state at time T" or "diffs since T"
- No daemon — materialization triggered by DB subscription callbacks

## 3. Persistent Agents + Subscriptions

- Real-time diffs dispatch immediately (no session load overhead)
- Hook registrations and tool access persist continuously
- Context resets per handoff (not process restarts)
- SpacetimeDB subscriptions feed directly into agent state

## 4. Shared Autoclave View

- Hook detects co-active agents via SpacetimeDB subscription
- Context shifts to shared-view mode (R-label drops to show mode change)
- Both agents see same state diffs, minimizing divergence
- Critic's diffs stream into architect's context as they arrive
- No polling — temporal subscriptions push diffs

## 5. MCP-Native Codex Server

- MCP server returns resources in codex engine format
- `mcp://belam/codex/t1` → returns primitive at coordinate
- R-label diffs as usage docs (transformation > explanation)
- codex_codec.py handles boundary translation
- External MCP clients (Cursor, Claude Desktop) get codex-native representations

## 6. Live Mode-Switch (e0x)

- Live-swap coordinate grammar mid-session
- Forces supermap re-render in new format
- Creates novel attention interference from forced re-mapping
- Research: quantify which token sequences produce most information-dense embeddings

## 7. Multi-Pane Rendering

- Tmux split: dense codex | JSON MCP equivalent | human-pretty view
- Auto-parser renders same workflow in all three simultaneously
- Debugging and teaching tool for token efficiency visualization

## Acceptance Criteria

- [ ] SpacetimeDB evaluation complete
- [ ] Temporal state prototype with diff generation
- [ ] `.codex` reactive materialization working
- [ ] Persistent agent + subscription proof of concept
- [ ] Shared autoclave view between 2 agents
- [ ] MCP server returning codex-native resources
- [ ] e0x live mode-switch functional
- [ ] Multi-pane tmux rendering prototype

## Dependencies
- v2 must be settled first (dense grammar, coordinate modes, RAM state)
- `tasks/temporal-interaction-llm-gaming.md` — shares SpacetimeDB evaluation
- `research-openclaw-internals` pipeline — hook architecture findings

## Notes
- Vector-direct encoding research (pre-tokenized representations → encoder) is v4+ territory
- Mobile viewport rendering fix can happen anytime as polish
