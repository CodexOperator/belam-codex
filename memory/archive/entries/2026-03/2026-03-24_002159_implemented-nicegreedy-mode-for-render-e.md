---
primitive: memory_log
timestamp: "2026-03-24T00:21:59Z"
category: technical
importance: 3
tags: []
source: "session"
content: "Implemented nice/greedy mode for render engine. Nice mode (default) defers all inotify processing to a queue and flushes only on UDS diff/supermap/my_diff queries — saves CPU between agent turns while keeping full history in RAM. Greedy mode is current live behavior with immediate processing and heartbeat trigger. Cockpit plugin updated to start engine with --mode nice. Discovered bug: cockpit plugin respawns engine without CLI args, overriding manual startup modes. Gateway also crashed during testing — recovery cron job discussion started. Session: 4fb6f15e, 2026-03-23."
status: consolidated
---

# Memory Entry

**2026-03-24T00:21:59Z** · `technical` · importance 3/5

Implemented nice/greedy mode for render engine. Nice mode (default) defers all inotify processing to a queue and flushes only on UDS diff/supermap/my_diff queries — saves CPU between agent turns while keeping full history in RAM. Greedy mode is current live behavior with immediate processing and heartbeat trigger. Cockpit plugin updated to start engine with --mode nice. Discovered bug: cockpit plugin respawns engine without CLI args, overriding manual startup modes. Gateway also crashed during testing — recovery cron job discussion started. Session: 4fb6f15e, 2026-03-23.

---
*Source: session*
*Tags: none*
