---
primitive: memory_log
timestamp: "2026-03-22T02:31:31Z"
category: context
importance: 3
tags: [instance:main, pipeline, plugin, decision, supermap]
source: "session"
content: "Retired pipeline-context plugin (renamed to pipeline-context.disabled). Decision: supermap injection already covers all active pipeline orientation. Plugin was burning prompt tokens on redundant stage history (200-500 chars per pipeline x 6 pipelines). Supermap is the single source of truth for pipeline status."
status: consolidated
---

# Memory Entry

**2026-03-22T02:31:31Z** · `context` · importance 3/5

Retired pipeline-context plugin (renamed to pipeline-context.disabled). Decision: supermap injection already covers all active pipeline orientation. Plugin was burning prompt tokens on redundant stage history (200-500 chars per pipeline x 6 pipelines). Supermap is the single source of truth for pipeline status.

---
*Source: session*
*Tags: instance:main, pipeline, plugin, decision, supermap*
