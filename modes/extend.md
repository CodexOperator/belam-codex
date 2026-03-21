---
primitive: mode
status: active
coordinate: e3
function: extend
applicable_namespaces: []
tags: [engine, mode, v2]
description: Extend the engine at runtime — register new namespaces and categories (session-scoped)
---

## e3 — Extend Mode

Extends the Codex Engine namespace at runtime. Changes are session-scoped;
persistent registration is planned for V3.

### Usage
  e3 category <name>              — register a new category directory
  e3 namespace <prefix> <dir>     — register a new namespace mapping
  e3                              — list all active extensions this session

### Examples
  e3 category experiments         — creates experiments/ dir, registers as 'ex'
  e3 namespace x experiments      — maps prefix 'x' to experiments/ directory

### Output
Each operation prints an F-label diff showing what changed:
  F7 + namespace 'x' -> experiments/ [session-scoped]

### Notes
- Extensions are in-memory only (this session)
- Persistent namespaces: edit NAMESPACE dict in codex_engine.py
- V3 will support a namespace registry file
