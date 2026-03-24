---
primitive: memory_log
timestamp: "2026-03-24T02:24:20Z"
category: event
importance: 3
tags: [instance:main, cron, gateway, watchdog, systemd, incident]
source: "session"
content: "Shael urgently disabled all cron jobs (OpenClaw gateway crons + system crontab) after gateway kept restarting/failing. Root cause: gateway_watchdog.sh (every 5 min via system crontab) was seeing broken systemd openclaw-gateway.service and trying to restart it, conflicting with actual gateway process running outside systemd (pid 3166693). systemd service crashes with 'Missing config' due to path/env issue. Re-enabled all crons except watchdog after diagnosis. Watchdog fix deferred."
status: active
---

# Memory Entry

**2026-03-24T02:24:20Z** · `event` · importance 3/5

Shael urgently disabled all cron jobs (OpenClaw gateway crons + system crontab) after gateway kept restarting/failing. Root cause: gateway_watchdog.sh (every 5 min via system crontab) was seeing broken systemd openclaw-gateway.service and trying to restart it, conflicting with actual gateway process running outside systemd (pid 3166693). systemd service crashes with 'Missing config' due to path/env issue. Re-enabled all crons except watchdog after diagnosis. Watchdog fix deferred.

---
*Source: session*
*Tags: instance:main, cron, gateway, watchdog, systemd, incident*
