---
primitive: task
status: open
priority: high
created: 2026-03-24
owner: belam
depends_on: [ram-git-worktree-bootstrap]
upstream: [codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing]
downstream: [ram-git-undo-primitive]
tags: [infrastructure, codex-engine, ram, git, diff]
project: codex-engine
pipeline_template: 
current_stage: 
pipeline_status: 
launch_mode: queued
---
# RAM Git Diff Pipeline

## Description

Replace inotify-based change detection with git-native diffs. Every agent write is a git object; `git diff` replaces the inotify→queue→flush chain.

Extracted from V4 task deliverable D7.2.

## Scope

1. `post-commit` hook → pings render engine UDS → diffs flow to agents next turn
2. Replaces inotify watches, change queue, flush worker
3. Coalescing is free (git handles atomic commits)
4. Ordering is free (commit sequence)
5. Turn boundary = commit boundary (cockpit plugin fires auto-commit on turn end)

## Success Criteria

- [ ] `git diff` replaces inotify for all diff generation
- [ ] Diffs visible to other attached agents in <5ms
- [ ] No inotify watches needed on primitive dirs
