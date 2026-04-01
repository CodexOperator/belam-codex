---
primitive: task
status: complete
priority: medium
created: 2026-03-24
owner: belam
depends_on: []
upstream: [limit-soul-read-write]
downstream: [primitive-access-compliance-tracking]
tags: [infrastructure, codex-engine, architecture, convention]
project: codex-engine
pipeline_template: 
current_stage: 
pipeline_status: 
launch_mode: queued
---
# Coordinate-First Boot Convention

## Description

Add a boot convention to AGENTS.md establishing that the coordinator (Soul instance) accesses primitive state exclusively through Codex Engine coordinates. Direct Read/Write/Edit on primitive files is reserved for non-primitive content (code, scripts, configs) and for sub-agents.

## Scope

1. Add convention to AGENTS.md: "Primitive state access via coordinates. Direct file access for non-primitive content only."
2. Add `--direct` override flag to the engine CLI for emergency direct file access
3. Document which paths are "primitive" (tasks/, decisions/, lessons/, etc.) vs "non-primitive" (scripts/, skills/, etc.)
4. Sub-agents retain full Read/Write access — the convention applies to coordinator only

## Success Criteria

- [ ] Convention documented in AGENTS.md
- [ ] `--direct` flag exists and logs usage
- [ ] Coordinator operates a full session without direct primitive file access
- [ ] Sub-agents unaffected
