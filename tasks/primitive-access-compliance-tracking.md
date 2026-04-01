---
primitive: task
status: open
priority: medium
created: 2026-03-24
owner: belam
depends_on: [coordinate-first-boot-convention]
upstream: [limit-soul-read-write]
downstream: []
tags: [infrastructure, codex-engine, observability]
project: codex-engine
pipeline_template: 
current_stage: 
pipeline_status: 
launch_mode: queued
---
# Primitive Access Compliance Tracking

## Description

Engine-level tracking of when agents access primitive files directly (bypassing coordinates). Provides visibility into compliance with the coordinate-first convention.

## Scope

1. Engine logs when Read/Write/Edit hits a primitive path (tasks/, decisions/, lessons/, memory/entries/, etc.)
2. Per-session summary: count of direct accesses vs coordinate accesses
3. Threshold alert: warn if direct access exceeds 5% of primitive interactions
4. Accessible via engine command (e.g. `R compliance` or similar)

## Success Criteria

- [ ] Direct primitive access logged with timestamp and path
- [ ] Per-session compliance percentage available
- [ ] Alert mechanism for threshold violations
- [ ] Data helps identify which workflows still need coordinate equivalents
