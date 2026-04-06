---
primitive: memory_log
timestamp: "2026-03-20T20:07:21Z"
category: technical
importance: 3
tags: [instance:main, codex-engine, boot-hook, infrastructure, supermap]
source: "session"
content: "Session 2a293aef: Wired Codex Engine V1 Supermap into session boot context. OpenClaw auto-injects only fixed files (AGENTS.md, SOUL.md, TOOLS.md, IDENTITY.md, USER.md, HEARTBEAT.md, BOOTSTRAP.md). Implemented workaround: added --boot flag to codex_engine.py that writes raw supermap content (bypassing R-label pin dedup), hooked into embed_primitives.py so AGENTS.md gets supermap embedded on every index rebuild. Added 'belam boot' command to belam.sh. Also fixed piping bug where pin-tracking was swallowing output in non-interactive use."
status: consolidated
---

# Memory Entry

**2026-03-20T20:07:21Z** · `technical` · importance 3/5

Session 2a293aef: Wired Codex Engine V1 Supermap into session boot context. OpenClaw auto-injects only fixed files (AGENTS.md, SOUL.md, TOOLS.md, IDENTITY.md, USER.md, HEARTBEAT.md, BOOTSTRAP.md). Implemented workaround: added --boot flag to codex_engine.py that writes raw supermap content (bypassing R-label pin dedup), hooked into embed_primitives.py so AGENTS.md gets supermap embedded on every index rebuild. Added 'belam boot' command to belam.sh. Also fixed piping bug where pin-tracking was swallowing output in non-interactive use.

---
*Source: session*
*Tags: instance:main, codex-engine, boot-hook, infrastructure, supermap*
