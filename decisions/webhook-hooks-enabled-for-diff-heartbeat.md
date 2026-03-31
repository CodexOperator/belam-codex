---
primitive: decision
slug: webhook-hooks-enabled-for-diff-heartbeat
title: Webhook Hooks Enabled for Diff-Triggered Heartbeat
importance: 3
tags: [instance:main, hooks, webhook, heartbeat, config]
created: 2026-03-23
promotion_status: exploratory
doctrine_richness: 6
contradicts: []
---

# Decision: Webhook Hooks Enabled for Diff-Triggered Heartbeat

## Context
The diff-triggered heartbeat architecture requires the render engine to POST to `/hooks/wake`. The OpenClaw webhook endpoint was previously disabled (no token set).

## Decision
Enable webhook hooks in `openclaw.json`:
- `hooks.enabled: true`
- `hooks.token`: generated secure random token
- `hooks.path: /hooks`

Token stored in hooks config, also injected into `codex_render.py` via `_load_hook_config()` which reads the gateway config at startup.

## Rationale
The `/hooks/wake` endpoint is the cleanest way for an external process (render engine) to inject a system event into the main session. Avoids need for custom IPC or writing to session files directly.

## Security Note
Token is a 43-char random string. The hooks endpoint is local-only (gateway runs on localhost:18789). Risk is low.

## Related
- upstream: diff-triggered-heartbeat-architecture
