---
primitive: decision
status: accepted
date: 2026-03-23
context: (add context)
alternatives: []
rationale: (add rationale)
consequences: []
upstream: [decision/codex-cockpit-before-prompt-build-per-turn-injection, lesson/render-engine-zombie-blocks-session-startup]
downstream: []
tags: [instance:main, render-engine, robustness, session-startup]
---

# render-engine-pid-file-and-force-flag

## Context

Zombie render engine processes were blocking new agent sessions from receiving supermap context via the cockpit plugin. The socket-only existence check was insufficient for stale process detection. Shael asked for robust clean startup so every `/new` session properly spawns into the render engine.

## Options Considered

- **Option A:** Just unlink the stale socket unconditionally on startup (risky — could kill a healthy engine).
- **Option B:** Add PID file + `--force` flag: UDS stop → PID kill with cmdline verification → fresh start (chosen).
- **Option C:** Multi-instance render engines (one per agent workspace) — deferred, not needed for main session.

## Decision

Add `--force` startup mode to `codex_render.py`: attempts graceful UDS stop, falls back to PID-file kill (with `/proc/{pid}/cmdline` verification to avoid recycled-PID false kills), then starts fresh. PID file written to `.codex_runtime/render.pid` on start, removed on clean shutdown. Cockpit plugin `ensureRenderEngine()` always passes `--force` and polls socket up to 3s (6 × 500ms). Committed as `a04ea56f` to belam-codex master.

## Consequences

- Every `/new` session gets clean render engine startup with supermap context injection via cockpit plugin.
- PID file enables future tooling (health checks, monitoring) to locate the engine process.
- Slight startup overhead (UDS probe + optional kill) is negligible vs. benefit of guaranteed clean state.
- Cockpit plugin is now the authoritative engine lifecycle manager for the main workspace.
