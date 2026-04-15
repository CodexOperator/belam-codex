---
primitive: lesson
date: 2026-04-15
source: main session 2026-04-14 — workspace migration debugging
confidence: high
upstream: []
downstream: [decision/hermes-first-workspace-resolution-cascade]
tags: [instance:main, workspace, plugins, hermes]
---

# plugin-hardcoded-paths-drift-on-workspace-move

## Context

The R CLI wrapper was patched to resolve workspace as Hermes-first (`~/.hermes/belam-codex`), but the supermap still wasn't appearing in agent context.

## What Happened

Two plugins had hardcoded paths to `~/.openclaw/workspace`: the openclaw_hooks Python plugin used `Path(__file__).parents[2]` (wrong when installed to `~/.hermes/plugins`), and the codex-cockpit TypeScript plugin had a hardcoded UDS socket path. Both silently failed — no errors, just missing context.

## Lesson

When workspace location changes, every component that touches it must be audited — hardcoded paths in plugins fail silently because they catch exceptions and return empty strings.

## Application

- After any workspace relocation, grep all plugins/scripts for the old path
- Prefer validated resolution cascades over hardcoded paths
- Silent-fail catch blocks in plugins make path bugs invisible — add logging or at minimum a debug flag
