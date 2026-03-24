---
primitive: mode
status: active
coordinate: e0
function: orchestrate
applicable_namespaces: [p, t, d, l, w]
composes_with: [view_flags]
operation_index:
  1: dispatch
  2: status
  3: gates
  4: locks
  5: complete
  6: block
  7: next
  8: archive
  9: launch
  10: kill
  11: restart
tags: [engine, mode, v2]
description: Orchestrate pipeline and task execution via numbered operations or named actions
---

## e0 — Orchestrate Mode

Routes operations to the orchestration engine for pipeline and task management.

### Usage
  e0                               — full orchestration sweep
  e0 <pipeline> <op> [args...]     — execute operation on a pipeline
  e0 <action> [args...]            — run a general action

### Operation Index (numeric shortcuts)
  1  dispatch   — dispatch agent to pipeline stage
  2  status     — show pipeline status
  3  gates      — check pipeline gates
  4  locks      — show active locks
  5  complete   — mark stage complete
  6  block      — block a stage
  7  next       — show next action
  8  archive    — archive a pipeline
  9  launch     — launch new pipeline
  10 kill       — kill running agent + reset state to last clean stage
  11 restart    — kill + re-dispatch from current stage

### Dot-Connector (.iN = "as persona")
  e0p1 1.i1     — dispatch pipeline 1 as architect (i1)
  e0p1 5.i2     — complete pipeline 1 as builder (i2)
  e0p1 1.i3     — dispatch pipeline 1 as critic (i3)

### Output Format (.1 = JSON)
  e0p1 2.1      — pipeline 1 status as JSON

### Dense Single-Letter Sub-Commands
  e0g           — gates (all pipelines)
  e0h           — handoffs
  e0s           — stalls
  e0k           — locks
  e0l           — list all pipelines
  e0r           — resume
  e0x           — kill (x = terminate running agent, reset state)

### Examples
  e0 p3 status                     — show pipeline 3 status
  e0p3 2                           — same, using numeric op
  e0p1 1.i1                        — dispatch p1 to architect
  e0 sweep                         — full orchestration sweep
  e0g p3                           — check gates for pipeline 3
  e0 p1 kill                       — kill pipeline 1's running agent, reset state
  e0 p1 restart                    — kill and re-dispatch pipeline 1 from current stage
  e0p1 10                          — same as kill, numeric shortcut
  e0 p1 kick                       — dispatch pending_action if unclaimed (dispatch failed/never claimed)

### Routing
Maps to orchestration_engine.py when available, falls back to legacy scripts.
View modifiers (-g, --depth, --as) compose orthogonally with e0 operations.

## Workflows

### .l1 — Full Pipeline Launch
1. `e0 t{n}` — launch pipeline from task (auto-creates, dispatches architect)
2. Wait for architect handoff notification
3. `e0 l` — list all pipeline states

### .l2 — Emergency Pipeline Block
1. `e0 p{n} block {stage}` — block pipeline stage with reason
2. Group chat notification is automatic (orchestrator handles it)
3. `e0g p{n}` — check gate status

### .l3 — Kill and Restart a Stuck Agent
1. `e0 p{n} kill` — terminate the running agent process, reset dispatch_claimed=false
2. Verify with `e0 p{n} status` — state should show dispatch_claimed=false, pending_action intact
3. `e0 p{n} restart` or `e0 p{n} kick` — re-dispatch from current pending_action
