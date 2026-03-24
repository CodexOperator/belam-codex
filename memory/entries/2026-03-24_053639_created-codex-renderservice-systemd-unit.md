---
primitive: memory_log
timestamp: "2026-03-24T05:36:39Z"
category: event
importance: 4
tags: [instance:main, render-engine, systemd, infrastructure]
source: "session"
content: "Created codex-render.service systemd unit on 2026-03-24. Service runs codex_render.py --mode nice --force, enabled at boot, RestartSec=5, MemoryMax=512M, Nice=10. Engine came up with 409 nodes indexed, supermap at /dev/shm/openclaw/supermap.txt (5162 bytes). Triggered by discovering render engine not running at session start (no PID, no supermap on ramdisk). Cockpit V7 plugin confirmed clean — reads supermap only, does not spawn engine. Heartbeat Task 5.5 added: check systemctl is-active, restart if down."
status: active
---

# Memory Entry

**2026-03-24T05:36:39Z** · `event` · importance 4/5

Created codex-render.service systemd unit on 2026-03-24. Service runs codex_render.py --mode nice --force, enabled at boot, RestartSec=5, MemoryMax=512M, Nice=10. Engine came up with 409 nodes indexed, supermap at /dev/shm/openclaw/supermap.txt (5162 bytes). Triggered by discovering render engine not running at session start (no PID, no supermap on ramdisk). Cockpit V7 plugin confirmed clean — reads supermap only, does not spawn engine. Heartbeat Task 5.5 added: check systemctl is-active, restart if down.

---
*Source: session*
*Tags: instance:main, render-engine, systemd, infrastructure*
