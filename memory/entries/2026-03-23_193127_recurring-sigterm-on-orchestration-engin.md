---
primitive: memory_log
timestamp: "2026-03-23T19:31:27Z"
category: event
importance: 3
tags: [instance:main, gateway, systemd, codex-engine-v4, orchestration]
source: "session"
content: "Recurring SIGTERM on orchestration engine during heartbeat tasks: e0 sweep and checkpoint logic both got SIGTERM before completion. Diagnosed as system-level timeout issue affecting heartbeat reliability. Also: gateway systemd service crashed at 18:04 UTC (restart loop, 12 restarts, missing config error) while actual gateway process (pid 2934107) remained alive and functional."
status: active
---

# Memory Entry

**2026-03-23T19:31:27Z** · `event` · importance 3/5

Recurring SIGTERM on orchestration engine during heartbeat tasks: e0 sweep and checkpoint logic both got SIGTERM before completion. Diagnosed as system-level timeout issue affecting heartbeat reliability. Also: gateway systemd service crashed at 18:04 UTC (restart loop, 12 restarts, missing config error) while actual gateway process (pid 2934107) remained alive and functional.

---
*Source: session*
*Tags: instance:main, gateway, systemd, codex-engine-v4, orchestration*
