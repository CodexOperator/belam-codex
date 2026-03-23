---
primitive: memory_log
timestamp: "2026-03-23T04:09:26Z"
category: technical
importance: 3
tags: [instance:main, supermap, agents-md, codex-cockpit, boot-hook]
source: "session"
content: "Shael reported stale supermap on initial boot — AGENTS.md had embedded supermap from --boot run on 2026-03-22 01:27 UTC (26h stale). Root cause: supermap-boot hook disabled but AGENTS.md still had old <!-- BEGIN:SUPERMAP --> block. Fix: stripped AGENTS.md from 87KB to 2KB, removing the embedded supermap. cockpit plugin handles per-turn injection. Also began deprecating --boot flag and adding --supermap-anchor/--supermap-diff flags to codex_engine.py."
status: active
---

# Memory Entry

**2026-03-23T04:09:26Z** · `technical` · importance 3/5

Shael reported stale supermap on initial boot — AGENTS.md had embedded supermap from --boot run on 2026-03-22 01:27 UTC (26h stale). Root cause: supermap-boot hook disabled but AGENTS.md still had old <!-- BEGIN:SUPERMAP --> block. Fix: stripped AGENTS.md from 87KB to 2KB, removing the embedded supermap. cockpit plugin handles per-turn injection. Also began deprecating --boot flag and adding --supermap-anchor/--supermap-diff flags to codex_engine.py.

---
*Source: session*
*Tags: instance:main, supermap, agents-md, codex-cockpit, boot-hook*
