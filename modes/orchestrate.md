---
primitive: mode
status: active
coordinate: e0
function: orchestrate
applicable_namespaces: [p, t, d, l, w]
tags: [engine, mode, v2]
description: Orchestrate pipeline and task execution via the action dispatch system
---

## e0 — Orchestrate Mode

Routes operations to the belam action dispatch engine.

### Usage
  e0 <coord> <action> [args...]   — execute action on a primitive
  e0 <action> [args...]           — run a general action
  e0                              — show this help

### Examples
  e0 p3 run                       — run pipeline 3
  e0 t1 complete                  — mark task 1 complete
  e0 status                       — show workspace status
  e0 autorun                      — trigger pipeline autorun

### Routing
Maps to execute_action() — all V1 -x flag behaviour applies.
