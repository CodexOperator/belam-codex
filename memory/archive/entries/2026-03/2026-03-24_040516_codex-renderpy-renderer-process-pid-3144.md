---
primitive: memory_log
timestamp: "2026-03-24T04:05:16Z"
category: technical
importance: 4
tags: [instance:main, renderer, codex-cockpit, gateway, freeze]
source: "session"
content: "codex_render.py renderer process (PID 3144387) was causing gateway contention. Kill attempts via exec were themselves being killed (SIGTERM, SIGKILL) — suggesting gateway resource conflict with renderer. Plan: disable codex-cockpit plugin via config to prevent auto-restart on gateway boot."
status: consolidated
---

# Memory Entry

**2026-03-24T04:05:16Z** · `technical` · importance 4/5

codex_render.py renderer process (PID 3144387) was causing gateway contention. Kill attempts via exec were themselves being killed (SIGTERM, SIGKILL) — suggesting gateway resource conflict with renderer. Plan: disable codex-cockpit plugin via config to prevent auto-restart on gateway boot.

---
*Source: session*
*Tags: instance:main, renderer, codex-cockpit, gateway, freeze*
