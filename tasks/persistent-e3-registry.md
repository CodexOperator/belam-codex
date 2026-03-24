---
primitive: task
status: open
priority: low
created: 2026-03-24
owner: belam
depends_on: []
upstream: [persistent-extend-and-indexed-subops]
downstream: [indexed-subops-e0-e3]
tags: [engine, extend, persistence, infrastructure]
project: codex-engine
---

# Persistent e3 Registry

## Description

Make e3 (extend mode) persistent across sessions. Currently e3 registers namespaces/categories in-memory only — extensions evaporate when the Python process exits.

## Scope

1. e3 writes to `config/engine_registry.yaml` (or similar persistent store)
2. Engine loads registry on startup, merges with hardcoded namespaces
3. e3 supports: register namespace, register category, register action
4. Registry survives session resets and gateway restarts
5. Render engine picks up new registry entries via inotify

## Success Criteria

- `e3 ns.action "description"` persists and is available in next session
- Registry file is human-readable YAML
- Existing hardcoded namespaces still work (registry is additive)
- Render engine indexes registered extensions
