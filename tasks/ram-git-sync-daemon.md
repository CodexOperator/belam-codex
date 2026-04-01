---
primitive: task
status: open
priority: high
created: 2026-03-24
owner: belam
depends_on: [ram-git-worktree-bootstrap]
upstream: [codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing]
downstream: []
tags: [infrastructure, codex-engine, ram, git, persistence]
project: codex-engine
pipeline_template: 
current_stage: 
pipeline_status: 
launch_mode: queued
---
# RAM Git Sync Daemon

## Description

Background daemon that periodically pushes RAM git state to disk for persistence. Ensures volatile tmpfs data survives crashes and reboots.

Extracted from V4 task deliverable D7.3.

## Scope

1. Periodic push: RAM git → disk git (configurable interval, default 60s)
2. Session-end flush: sync on agent session end
3. Crash recovery: systemd ExecStartPre clones disk → RAM on boot
4. Sync uses `git push` — fast, incremental, atomic
5. Disk staleness target: <60s

## Success Criteria

- [ ] Sync daemon maintains <60s staleness on disk
- [ ] Clean recovery after simulated crash (kill -9 engine → restart)
- [ ] Session-end flush verified working
