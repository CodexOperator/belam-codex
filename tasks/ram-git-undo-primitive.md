---
primitive: task
status: open
priority: medium
created: 2026-03-24
owner: belam
depends_on: [ram-git-diff-pipeline]
upstream: [codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing]
downstream: []
tags: [infrastructure, codex-engine, ram, git, undo]
project: codex-engine
---

# Undo Primitive via RAM Git

## Description

Turn-level undo as a first-class coordinate action. Since turn boundary = commit boundary, undo is simply `git reset --hard HEAD~N` on the RAM repo.

Extracted from V4 task deliverable D7.6.

## Scope

1. `e1 undo` → roll back last turn (HEAD~1) in RAM repo
2. `e1 undo N` → roll back N turns
3. Undo is RAM-only until next sync — disk stays clean as confirmation boundary
4. Adds to coordinate grammar as a first-class action

## Success Criteria

- [ ] `e1 undo` rolls back last turn in <10ms
- [ ] Multi-turn undo works cleanly
- [ ] Disk remains at pre-undo state until sync confirms
