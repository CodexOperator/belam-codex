---
primitive: task
status: open
priority: medium
created: 2026-03-21
owner: belam
depends_on: [codex-engine-v2-modes-mcp-temporal]
upstream: [decision/codex-engine-v2-dense-alphanumeric-grammar]
downstream: []
tags: [engine, codex, mcp, v3]
---

# Codex Engine v3: MCP Native, Live Mode-Switch, Multi-Pane Rendering

## Description

After v2 settles (dense grammar + coordinate modes), extend the addressing/format layer with MCP-native serving, live grammar switching, and multi-view rendering. Pure codex engine scope — no orchestration or agent coordination.

## 1. MCP-Native Codex Server

- MCP server returns resources in codex engine format
- `mcp://belam/codex/t1` → returns primitive at coordinate
- R-label diffs as usage docs (transformation > explanation)
- codex_codec.py handles boundary translation
- External MCP clients (Cursor, Claude Desktop) get codex-native representations

## 2. Live Mode-Switch (e0x)

- Live-swap coordinate grammar mid-session
- Forces supermap re-render in new format
- Creates novel attention interference from forced re-mapping
- Research: quantify which token sequences produce most information-dense embeddings

## 3. Reactive .codex Materialization

- `.codex` files as materialized views (format layer, not state source)
- `before_prompt_build` reads fresh `.codex` each turn
- Agent sees temporal diff in context — "state at time T" or "diffs since T"
- No daemon — materialization triggered by callbacks from whatever state backend exists

## 4. Multi-Pane Rendering

- Tmux split: dense codex | JSON MCP equivalent | human-pretty view
- Auto-parser renders same workflow in all three simultaneously
- Debugging and teaching tool for token efficiency visualization

## Acceptance Criteria

- [ ] MCP server returning codex-native resources
- [ ] codex_codec.py wired into MCP response pipeline
- [ ] e0x live mode-switch functional
- [ ] `.codex` reactive materialization prototype
- [ ] Multi-pane tmux rendering prototype

## Dependencies
- Codex Engine v2 must be settled first
- `research-openclaw-internals` pipeline — hook architecture findings

## Notes
- Vector-direct encoding research (pre-tokenized representations → encoder) is v4+ territory
- Mobile viewport rendering fix can happen anytime as polish
