---
primitive: mode
status: active
coordinate: e2
function: create
applicable_namespaces: [p, t, d, l, w, k, s, c]
tags: [engine, mode, v2]
description: Create new primitives via the create_primitive scaffolding system
---

## e2 — Create Mode

Creates new primitives using the create_primitive.py scaffolding system.
For command primitives (c), auto-scaffolds a pending ACTION_REGISTRY entry.

### Usage
  e2 <type_prefix> <title>        — create a new primitive
  e2                              — show this help

### Type Prefixes
  t   task
  d   decision
  l   lesson
  w   project/workspace
  c   command
  s   skill
  k   knowledge

### Examples
  e2 t "Fix parser edge case"     — create a task
  e2 d "Use YAML frontmatter"     — create a decision
  e2 c "sync-remote"              — create a command primitive

### Routing
Maps to execute_create() — all V1 -n flag behaviour applies.
