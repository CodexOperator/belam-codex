---
primitive: decision
status: accepted
date: 2026-03-24
context: supermap-legend-not-injecting-into-agent-context
alternatives: []
rationale: Without allowPromptInjection, before_prompt_build return is silently dropped
consequences: [supermap-and-legend-will-appear-in-context]
upstream: []
downstream: []
tags: [instance:main, cockpit, plugin, config]
importance: 4
---

# codex-cockpit-allowpromptinjection-required

## Context

Shael asked why the supermap and legend weren't appearing in agent context despite the codex-cockpit plugin loading. Only the Coordinate Mode scaffold (baked into system prompt template) was showing — the actual supermap tree and codex legend from the plugin were missing.

## Options Considered

- **Option A:** Add `hooks.allowPromptInjection: true` to `plugins.entries.codex-cockpit` config — enables before_prompt_build hook return values to reach the agent.
- **Option B:** Find another mechanism to inject context — unnecessary, the existing before_prompt_build approach is correct.

## Decision

Add `hooks.allowPromptInjection: true` to `plugins.entries.codex-cockpit` in OpenClaw config. Without this, `before_prompt_build` hook return values (`prependSystemContext` with supermap+legend) are silently dropped, causing the cockpit plugin to appear functional but fail to inject the actual supermap tree and codex legend.

## Consequences

- Supermap tree and codex legend will appear in agent context on each session start
- Cockpit plugin will be fully functional, not just scaffold-visible
- Discovered 2026-03-24 during diagnosis session
