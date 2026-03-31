---
primitive: lesson
date: 2026-03-22
source: main session 2026-03-22
confidence: confirmed
importance: 3
upstream: []
downstream: []
tags: [instance:main, plugin, openclaw, config, infrastructure]
promotion_status: candidate
doctrine_richness: 8
contradicts: []
---

# plugin-allowlist-must-be-updated-on-plugin-retire

## Context

Retiring a plugin by renaming its directory to `.disabled` prevents OpenClaw from loading the plugin code, but `openclaw.json` still lists it in `plugins.allow`. When an agent is spawned, OpenClaw validates `plugins.allow` against actually-loadable plugins and fails with a config error if a listed plugin is missing.

## What Happened

After renaming `pipeline-context` → `pipeline-context.disabled`, the next heartbeat attempted to dispatch the codex-engine-v3 architect agent. The agent failed to spawn because OpenClaw config validation rejected the stale `pipeline-context` entry in `plugins.allow`. Fixed by removing it from the allowlist.

## Lesson

Retiring a plugin requires **two steps**: (1) rename/disable the plugin directory, and (2) remove the plugin from `plugins.allow` in `openclaw.json`. Missing step 2 blocks all agent spawning.

## Application

Any time a plugin is disabled or removed, immediately update `openclaw.json` to remove it from `plugins.allow` and `plugins.entries`. Automate this if possible (have the retire script update both).
