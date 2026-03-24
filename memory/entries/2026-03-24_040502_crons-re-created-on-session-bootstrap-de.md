---
primitive: memory_log
timestamp: "2026-03-24T04:05:02Z"
category: technical
importance: 4
tags: [instance:main, cron, gateway, freeze]
source: "session"
content: "Crons re-created on session bootstrap despite being disabled. 'Memory consolidation check' (every 6h) and 'Daily memory consolidation' (every 24h) both targeted sessionTarget:main with wakeMode:now — meaning they inject system events directly into the main session and force-wake the gateway. Both newly disabled this session. Root cause of recurring gateway freezes."
status: active
---

# Memory Entry

**2026-03-24T04:05:02Z** · `technical` · importance 4/5

Crons re-created on session bootstrap despite being disabled. 'Memory consolidation check' (every 6h) and 'Daily memory consolidation' (every 24h) both targeted sessionTarget:main with wakeMode:now — meaning they inject system events directly into the main session and force-wake the gateway. Both newly disabled this session. Root cause of recurring gateway freezes.

---
*Source: session*
*Tags: instance:main, cron, gateway, freeze*
