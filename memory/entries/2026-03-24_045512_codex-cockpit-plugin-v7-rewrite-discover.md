---
primitive: memory_log
timestamp: "2026-03-24T04:55:12Z"
category: technical
importance: 4
tags: [instance:main, codex-cockpit, plugin, supermap, prependSystemContext, v7]
source: "session"
content: "Codex-cockpit plugin V7 rewrite: discovered appendSystemContext was not reliably reaching agents. Fixed by consolidating all injections (supermap, legend, scaffold) into prependSystemContext in correct order: supermap first, then Soul/identity legend, then coordinate mode scaffold. Gateway restart confirmed injection working at 04:39 UTC."
status: active
---

# Memory Entry

**2026-03-24T04:55:12Z** · `technical` · importance 4/5

Codex-cockpit plugin V7 rewrite: discovered appendSystemContext was not reliably reaching agents. Fixed by consolidating all injections (supermap, legend, scaffold) into prependSystemContext in correct order: supermap first, then Soul/identity legend, then coordinate mode scaffold. Gateway restart confirmed injection working at 04:39 UTC.

---
*Source: session*
*Tags: instance:main, codex-cockpit, plugin, supermap, prependSystemContext, v7*
