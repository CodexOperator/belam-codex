---
primitive: memory_log
timestamp: "2026-03-23T19:31:05Z"
category: event
importance: 3
tags: [instance:main, gateway, telegram, lane-queue, system-events]
source: "session"
content: "Telegram unresponsive for ~3min due to main session lane queue backup: system events (exec failures, diff-trigger at 10 F-labels, stall recovery SIGTERM) all piled into main session queue simultaneously, blocking interactive DMs. Lane wait reached 299 seconds (waitedMs=299279). Gateway also hit Telegram ETIMEDOUT and fell back to IPv4-only. System recovered once queue drained."
status: consolidated
---

# Memory Entry

**2026-03-23T19:31:05Z** · `event` · importance 3/5

Telegram unresponsive for ~3min due to main session lane queue backup: system events (exec failures, diff-trigger at 10 F-labels, stall recovery SIGTERM) all piled into main session queue simultaneously, blocking interactive DMs. Lane wait reached 299 seconds (waitedMs=299279). Gateway also hit Telegram ETIMEDOUT and fell back to IPv4-only. System recovered once queue drained.

---
*Source: session*
*Tags: instance:main, gateway, telegram, lane-queue, system-events*
