---
primitive: lesson
date: 2026-03-24
source: cockpit-plugin-supermap-diagnosis
confidence: high
upstream: []
downstream: []
tags: [instance:main, cockpit, plugin, hooks, gotcha]
importance: 3
---

# session-reset-not-a-valid-plugin-hook

## Context

Debugging codex-cockpit plugin. Plugin was registering `api.on('session_reset', ...)` to clear state on compaction/session-reset events.

## What Happened

OpenClaw logged: `unknown typed hook session_reset ignored (plugin=codex-cockpit...)`. The hook was silently dropped. The valid compaction hook is `after_compaction`, not `session_reset`.

## Lesson

`session_reset` is not a valid plugin hook name in OpenClaw. Plugin hooks use underscore_separated names (`agent_end`, `before_prompt_build`, `after_compaction`) — verify hook names against the hook catalog before registering.

## Application

When writing or modifying plugins, verify hook names against the official hook catalog. Watch for `unknown typed hook ... ignored` in gateway logs as a signal that a hook name is wrong.
