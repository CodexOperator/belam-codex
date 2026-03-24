---
primitive: memory_log
timestamp: "2026-03-24T02:54:29Z"
category: event
importance: 3
tags: [instance:main, gateway, openclaw, telegram, stability]
source: "session"
content: "Gateway freeze at 02:31 UTC traced to stale OpenClaw version: running 2026.3.12, latest was 2026.3.23-1 (11 days behind). Fixed by removing stale global npm install (/usr/lib/node_modules/openclaw), adding ~/.npm-global/bin to PATH, and restarting. Cron jobs disabled during investigation, safe consolidation crons re-enabled after update."
status: active
---

# Memory Entry

**2026-03-24T02:54:29Z** · `event` · importance 3/5

Gateway freeze at 02:31 UTC traced to stale OpenClaw version: running 2026.3.12, latest was 2026.3.23-1 (11 days behind). Fixed by removing stale global npm install (/usr/lib/node_modules/openclaw), adding ~/.npm-global/bin to PATH, and restarting. Cron jobs disabled during investigation, safe consolidation crons re-enabled after update.

---
*Source: session*
*Tags: instance:main, gateway, openclaw, telegram, stability*
