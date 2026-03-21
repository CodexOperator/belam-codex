---
primitive: decision
date: 2026-03-21
status: in-progress
importance: 4
upstream: []
downstream: []
tags:
  - instance:main
  - codex-cockpit
  - before_prompt_build
  - openclaw-plugin
  - supermap
  - cockpit
---

# codex-cockpit: Use before_prompt_build for Per-Turn Supermap Injection

## Decision

Implement a workspace plugin (`codex-cockpit`) that hooks `before_prompt_build` to
regenerate and inject the Codex Engine supermap on **every agent turn**, replacing
the one-shot `agent:bootstrap` approach used by the existing `supermap-boot` hook.

## Context

The `supermap-boot` hook injects CODEX.codex once at session start. After the first
turn, the supermap goes stale — new tasks, decisions, and lessons created during a
session are invisible without an explicit `exec` call to regenerate. This makes the
cockpit vision (letter-convention navigation, no exec for orientation) impossible.

## Rationale

- `PluginHookBeforePromptBuildResult.appendSystemContext` injects context cached-
  compatibly before each model call
- Supermap renders in ~164ms and produces ~3.5KB — well within per-turn budget
- `appendSystemContext` is used for static/semi-static plugin guidance, avoiding
  per-turn token cost inflation compared to `prependContext`
- The cockpit goal is zero `exec` for orientation; always-fresh supermap achieves it

## Trade-offs

- Every turn runs `python3 scripts/codex_engine.py --supermap` (+164ms latency)
- Supermap is ~3.5KB added to every prompt; acceptable for context budget
- Plugin load errors are non-fatal (hook silently skips on exception)

## Plugin Location

`/home/ubuntu/.openclaw/extensions/codex-cockpit/`

## Status

Plugin scaffolded. Initial load failed due to incorrect `definePluginEntry` import
pattern. Correct import structure identified from stock plugins. Resolution ongoing.
