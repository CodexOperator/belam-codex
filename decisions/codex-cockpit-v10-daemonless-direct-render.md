---
primitive: decision
status: accepted
date: 2026-03-25
context: After render engine simplification stripped DiffEntry/DiffEngine/inotify, the daemon's only remaining job was writing supermap.txt via UDS poke.
alternatives: [keep-daemon-running, uds-poke-to-write-file]
rationale: Replacing UDS poke with direct script call eliminates the daemon, socket, health check heartbeat, and /dev/shm file path dependency.
consequences: [codex_render-archived, systemd-service-disabled, render_supermap-single-entry-point, r0-coordinate-added]
upstream: [render-engine-simplification-subtract-before-build]
downstream: []
tags: [instance:main, codex-engine, cockpit, infrastructure, simplification]
---

# codex-cockpit-v10-daemonless-direct-render

## Context

After render-engine-simplification pipeline completed (Phase 1+2), the codex_render.py daemon was stripped of all DiffEntry, DiffEngine, StatPoller, and HeartbeatTrigger logic. Its only remaining function was: receive UDS poke → call render_supermap() → write /dev/shm/openclaw/supermap.txt. Shael asked whether the supermap was still updating without the daemon.

## Options Considered

- **Option A (keep daemon):** Keep codex_render.py running as a daemon, cockpit pokes via UDS each turn.
- **Option B (direct script):** Replace UDS poke with direct `execFileSync('python3 render_supermap.py')` in the cockpit plugin. Supermap rendered on-demand, returned via stdout, injected straight into context.

## Decision

V10 direct render: cockpit plugin calls render_supermap.py directly each turn. No daemon, no socket, no file write required. codex_render.py archived to scripts/archived/. systemd codex-render.service disabled. All codex_render imports in codex_engine.py and orchestration_engine.py stubbed/removed. r0 coordinate added for manual on-demand refresh in cockpit and CLI.

## Consequences

- render_supermap.py is the single entry point for supermap rendering
- Namespace discovery (_scan_namespaces) auto-detects new .namespace directories on each render call
- No persistent process to manage or restart after gateway changes
- r0 gives users/agents a manual trigger without needing daemon knowledge
