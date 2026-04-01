---
primitive: task
status: complete
priority: medium
created: 2026-03-24
owner: belam
depends_on: [ram-git-diff-pipeline]
upstream: [codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing]
downstream: []
tags: [infrastructure, codex-engine, ram, git, pipelines, signaling]
project: codex-engine
pipeline_template: 
current_stage: 
pipeline_status: 
launch_mode: queued
---
# Pipeline Turn-by-Turn Signaling + Ping Modes

## Description

Git-native signaling between pipeline agents and coordinator. Configurable granularity modes for different pipeline phases.

Extracted from V4 task deliverables D7.5 and D7.7.

## Scope

1. **Turn-by-turn signaling (D7.5):**
   - Instant wake on `_state.json` commit (pattern-match in post-commit hook)
   - Directive file convention: coordinator writes `_directive.md`, agent sees as diff
   - State file changes bypass diff accumulator threshold

2. **Ping/pong granularity modes (D7.7):**
   - `batch` — diffs accumulate, 10-threshold wake (background pipelines)
   - `stage` — wake on `_state.json` commit only (default, normal flow)
   - `turn` — every agent commit wakes coordinator (active debugging)
   - `live` — post-commit fires on every write (real-time observation)
   - Mode set per-pipeline in `_state.json` (`ping_mode: batch|stage|turn|live`)

## Success Criteria

- [ ] Pipeline state changes wake coordinator within 1 turn
- [ ] Ping mode configurable per-pipeline
- [ ] Default `stage` mode works without configuration
- [ ] `live` mode enables real-time pipeline observation
