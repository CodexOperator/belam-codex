---
primitive: memory_log
timestamp: "2026-03-24T20:35:35Z"
category: technical
importance: 3
tags: [instance:main, heartbeat, pipeline, rate-limiting, infrastructure]
source: "session"
content: "Shael requested Task 5 (pipeline queue) in HEARTBEAT.md run only every 12h instead of every 30m. Rather than changing the global heartbeat interval (agents.defaults.heartbeat.every), a timestamp gate was implemented: Task 5 checks /tmp/openclaw_last_pipeline_check.ts and skips if less than 12h has elapsed, then updates the timestamp after each evaluation. The global heartbeat remains at 30m for git commits, memory maintenance, render health, etc."
status: consolidated
---

# Memory Entry

**2026-03-24T20:35:35Z** · `technical` · importance 3/5

Shael requested Task 5 (pipeline queue) in HEARTBEAT.md run only every 12h instead of every 30m. Rather than changing the global heartbeat interval (agents.defaults.heartbeat.every), a timestamp gate was implemented: Task 5 checks /tmp/openclaw_last_pipeline_check.ts and skips if less than 12h has elapsed, then updates the timestamp after each evaluation. The global heartbeat remains at 30m for git commits, memory maintenance, render health, etc.

---
*Source: session*
*Tags: instance:main, heartbeat, pipeline, rate-limiting, infrastructure*
