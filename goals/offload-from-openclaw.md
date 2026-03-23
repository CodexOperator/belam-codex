---
primitive: goal
status: active
priority: high
created: 2026-03-23
owner: belam
tags: [infrastructure, independence, lightweight, codex-layer]
---

# Offload from OpenClaw to Lightweight Script System

## Vision

The codex engine + legendary map + pipeline orchestrator is already a near-complete agent coordination system. OpenClaw currently provides: channel routing (Telegram), session management, plugin hooks, and workspace file injection.

Most of those are replaceable:
- **Channel routing:** Direct API calls to Telegram/Anthropic
- **Session management:** The orchestration engine already handles agent lifecycle
- **Plugin hooks:** The codex-cockpit plugin does what we need; can be a standalone script
- **Workspace file injection:** The LM + supermap IS the context injection, and it's better

## What's Missing

1. **Direct API bridge** — script that talks to Claude API (or Claude Max) and routes to/from Telegram
2. **Session persistence** — conversation history storage (SQLite, same as monitoring)
3. **Heartbeat scheduler** — cron or systemd timer replacing OpenClaw's heartbeat polling
4. **Sub-agent spawning** — direct API calls instead of OpenClaw's sessions_spawn

## Why

- Dramatically lower overhead (no Node.js daemon, no plugin system)
- Full control over context window (no injected docs we don't want)
- Works with Claude Max subscription ($100/mo unlimited) or direct API
- The codex system IS the operating system — OpenClaw becomes unnecessary middleware
