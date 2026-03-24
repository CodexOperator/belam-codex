---
primitive: memory_log
timestamp: "2026-03-24T04:55:18Z"
category: technical
importance: 3
tags: [instance:main, codex-cockpit, render-engine, anchor, uds, supermap]
source: "session"
content: "Added anchor-triggered fresh render: codex_render.py supermap UDS handler now calls _write_supermap_file() after every query, so plugin execFileSync UDS poke on anchor turns forces engine to flush+render+write fresh supermap.txt to /dev/shm. Render engine restarted at 04:47 UTC; supermap.txt mtime updated confirming fix works."
status: active
---

# Memory Entry

**2026-03-24T04:55:18Z** · `technical` · importance 3/5

Added anchor-triggered fresh render: codex_render.py supermap UDS handler now calls _write_supermap_file() after every query, so plugin execFileSync UDS poke on anchor turns forces engine to flush+render+write fresh supermap.txt to /dev/shm. Render engine restarted at 04:47 UTC; supermap.txt mtime updated confirming fix works.

---
*Source: session*
*Tags: instance:main, codex-cockpit, render-engine, anchor, uds, supermap*
