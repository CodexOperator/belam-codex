---
primitive: lesson
date: 2026-03-24
source: cockpit-plugin-supermap-diagnosis
confidence: high
upstream: []
downstream: []
tags: [instance:main, cockpit, plugin, before_prompt_build, gotcha]
importance: 4
---

# before-prompt-build-requires-allowpromptinjection

## Context

Debugging why codex-cockpit plugin's supermap and legend weren't appearing in agent context, despite the plugin loading and the Coordinate Mode scaffold showing up.

## What Happened

The `before_prompt_build` hook was registered and firing, but its `prependSystemContext` return value was silently dropped. OpenClaw gates prompt-mutating hooks behind a config flag: `hooks.allowPromptInjection: true` in the plugin's entry in `plugins.entries`. Without this flag, hook registration succeeds and fires, but mutations never reach the agent.

## Lesson

The `before_prompt_build` plugin hook is a prompt-mutating hook gated behind `plugins.entries.<plugin>.hooks.allowPromptInjection: true`. Without this flag, OpenClaw accepts the hook registration but silently drops its `prependSystemContext`/`appendSystemContext` return value. The plugin appears to load fine and hook registration succeeds, but prompt mutations never reach the agent.

## Application

Always set `allowPromptInjection: true` in the plugin config entry for any plugin using `before_prompt_build`. When a plugin seems functional but context injections aren't appearing, check this flag first.
