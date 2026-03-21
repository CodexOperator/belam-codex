---
primitive: lesson
date: 2026-03-21
source: session c7bf31ab (codex-cockpit implementation)
confidence: high
importance: 4
upstream: []
downstream: []
tags:
  - instance:main
  - openclaw-plugin
  - plugin-sdk
  - before_prompt_build
  - codex-cockpit
---

# openclaw-plugin-definePluginEntry-import-path

## Context

Building the `codex-cockpit` workspace plugin to use the `before_prompt_build` hook
for per-turn supermap injection. First attempt at writing the plugin entry used
`definePluginEntry` imported from `openclaw/plugin-sdk/core`.

## What Happened

Plugin loaded but failed immediately: `TypeError: (0 , _core.definePluginEntry) is not a function`.

Inspecting stock plugins (diffs, device-pair) revealed the correct pattern:
- Import type `OpenClawPluginApi` from `openclaw/plugin-sdk/<submodule>`
- Export a plain object (not a function wrapper) with `id`, `name`, `description`, and `register(api)`
- **Do NOT use `definePluginEntry`** — it is not exposed in the plugin SDK surface

The `core.d.ts` / `core.js` file re-exports from the plugin SDK but `definePluginEntry`
is not one of the exported symbols despite appearing in internal type definitions.

## Lesson

Workspace plugins must export a plain object with `{ id, name, description, register(api) }` and import from `openclaw/plugin-sdk/<specific-submodule>`; `definePluginEntry` is NOT a valid SDK export.

## Application

Every time a new OpenClaw workspace plugin is written:
1. Copy the structure from a known-good stock plugin (e.g., diffs plugin's `import type { OpenClawPluginApi } from "openclaw/plugin-sdk/diffs"`)
2. Export a plain const object — not a function call or wrapper
3. Do not reference `definePluginEntry` anywhere
