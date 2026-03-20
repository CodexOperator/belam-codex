---
primitive: memory_log
timestamp: "2026-03-18T21:57:28Z"
category: technical
importance: 4
tags: [infrastructure, memory, boot]
source: "session"
content: "Extended MEMORY_CONTENT embed to include recent daily consolidated entries (today + yesterday full, day-before ★★★★+ only) alongside weekly/monthly rollups. Deduplicates entries across consolidation runs within a day. Budget bumped to 40k chars (currently ~30k used). New sessions now wake with 3 days of operational context + medium-term patterns inline — zero extra file reads needed for recent context."
status: consolidated
upstream: [decision/memory-as-primitive-type]
---

# Memory Entry

**2026-03-18T21:57:28Z** · `technical` · importance 4/5

Extended MEMORY_CONTENT embed to include recent daily consolidated entries (today + yesterday full, day-before ★★★★+ only) alongside weekly/monthly rollups. Deduplicates entries across consolidation runs within a day. Budget bumped to 40k chars (currently ~30k used). New sessions now wake with 3 days of operational context + medium-term patterns inline — zero extra file reads needed for recent context.

---
*Source: session*
*Tags: infrastructure, memory, boot*
