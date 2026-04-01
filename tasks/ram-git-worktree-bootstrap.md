---
primitive: task
status: open
priority: high
created: 2026-03-24
owner: belam
depends_on: []
upstream: [codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing]
downstream: [ram-git-diff-pipeline, ram-git-sync-daemon]
tags: [infrastructure, codex-engine, ram, git, symlinks]
project: codex-engine
pipeline_template: 
current_stage: 
pipeline_status: 
launch_mode: queued
---
# RAM Git Worktree Bootstrap + Symlinks

## Description

Set up the foundational layer: git repo in tmpfs with symlinks from workspace primitive dirs. Agents read/write through symlinks transparently — they don't know they're in RAM.

Extracted from V4 task deliverables D7.1 and D7.8.

## Scope

1. **D7.1 — RAM repo bootstrap:** On engine start, clone workspace → `/dev/shm/codex/` (primitive dirs only)
2. **D7.8 — Symlink routing:** Primitive namespace dirs symlinked from workspace → tmpfs
   - Symlinked: tasks/, decisions/, lessons/, memory/entries/, pipeline_builds/, pipelines/, goals/, knowledge/, projects/, workspaces/
   - On disk: AGENTS.md, SOUL.md, IDENTITY.md, USER.md, MEMORY.md, HEARTBEAT.md, skills/, scripts/, commands/, modes/, templates/, docs/
3. Crash recovery: `ExecStartPre=git clone disk → RAM` in systemd unit
4. Graceful degradation: if tmpfs unavailable, fall back to disk-direct

## Success Criteria

- [ ] Agent file writes resolve to RAM via symlinks (<1ms I/O)
- [ ] Symlinks invisible to all existing prompts/skills
- [ ] Engine restart from cold (disk clone → RAM) in <3s
- [ ] Zero agent-facing changes
