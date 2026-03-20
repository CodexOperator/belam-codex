---
primitive: memory_log
timestamp: "2026-03-20T22:01:04Z"
category: technical
importance: 4
tags: [instance:main, boot-context, memory-cleanup, embed-primitives, supermap, infrastructure]
source: "session"
content: "Boot context cleanup: AGENTS.md 15.9KB→2.2KB (−86%), MEMORY.md 14.8KB→2.6KB (−82%). Removed stale static primitive tree and memory hierarchy from boot files. Archived embed_primitives.py → archive/ (supermap hook replaced it). Updated HEARTBEAT.md Task 7 to drop embed_primitives call. _run_embed_primitives() in codex_engine.py now no-op stub. Supermap hook (CODEX.codex) is now the sole primitive index, rendered fresh at boot. Net: ~25KB stale context eliminated per session."
status: active
---

# Memory Entry

**2026-03-20T22:01:04Z** · `technical` · importance 4/5

Boot context cleanup: AGENTS.md 15.9KB→2.2KB (−86%), MEMORY.md 14.8KB→2.6KB (−82%). Removed stale static primitive tree and memory hierarchy from boot files. Archived embed_primitives.py → archive/ (supermap hook replaced it). Updated HEARTBEAT.md Task 7 to drop embed_primitives call. _run_embed_primitives() in codex_engine.py now no-op stub. Supermap hook (CODEX.codex) is now the sole primitive index, rendered fresh at boot. Net: ~25KB stale context eliminated per session.

---
*Source: session*
*Tags: instance:main, boot-context, memory-cleanup, embed-primitives, supermap, infrastructure*
