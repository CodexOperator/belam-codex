---
primitive: memory_log
timestamp: "2026-03-23T17:25:35Z"
category: event
importance: 4
tags: [instance:main, render-engine, codex-cockpit, robustness, session-startup]
source: "session"
content: "Render engine zombie process bug diagnosed and fixed. Shael asked if agent properly spawns into render engine on new sessions. Investigation revealed zombie processes from prior sessions blocked fresh engine starts (socket held by dead process). Fixed codex_render.py: (1) PID file written to .codex_runtime/render.pid on start/cleaned on stop, (2) --force CLI flag: sends stop via UDS, waits, kills by PID if needed (verifies /proc/{pid}/cmdline), (3) stale PID cleanup on startup if socket gone but PID file exists. Cockpit plugin updated to pass --force on ensureRenderEngine() and poll socket up to 3s. Committed to belam-codex master (a04ea56f)."
status: active
---

# Memory Entry

**2026-03-23T17:25:35Z** · `event` · importance 4/5

Render engine zombie process bug diagnosed and fixed. Shael asked if agent properly spawns into render engine on new sessions. Investigation revealed zombie processes from prior sessions blocked fresh engine starts (socket held by dead process). Fixed codex_render.py: (1) PID file written to .codex_runtime/render.pid on start/cleaned on stop, (2) --force CLI flag: sends stop via UDS, waits, kills by PID if needed (verifies /proc/{pid}/cmdline), (3) stale PID cleanup on startup if socket gone but PID file exists. Cockpit plugin updated to pass --force on ensureRenderEngine() and poll socket up to 3s. Committed to belam-codex master (a04ea56f).

---
*Source: session*
*Tags: instance:main, render-engine, codex-cockpit, robustness, session-startup*
