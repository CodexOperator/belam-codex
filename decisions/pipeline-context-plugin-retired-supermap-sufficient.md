---
primitive: decision
status: active
date: 2026-03-22
importance: 3
upstream: [supermap-boot-hook-via-embed-primitives]
downstream: []
tags: [instance:main, pipeline, plugin, supermap, prompt-optimization]
promotion_status: promoted
doctrine_richness: 7
contradicts: []
---

# pipeline-context-plugin-retired-supermap-sufficient

## Context

The `pipeline-context` plugin was injecting active pipeline status + recent stage history into every agent's system prompt via the `before_prompt_build` hook. This was designed to avoid the "read pipeline state" ceremony at session start. However, the supermap (via `supermap-boot` hook) was already injecting all active pipeline status and priority.

## Options Considered

- **Option A:** Keep pipeline-context plugin alongside supermap
- **Option B:** Retire pipeline-context plugin — let supermap be the single source

## Decision

Retired the `pipeline-context` plugin (renamed to `pipeline-context.disabled`). Also removed it from `plugins.allow` in `openclaw.json`.

## Consequences

- Cleaner, leaner boot prompts — fewer redundant tokens (~1800 chars saved per session boot)
- Agents use coordinate navigation for stage detail rather than having it injected
- Any future pipeline-adjacent boot context goes into the supermap, not a separate plugin
- Principle established: supermap is the single source of truth for active context
