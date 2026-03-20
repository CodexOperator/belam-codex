---
primitive: memory_log
timestamp: "2026-03-19T20:48:01Z"
category: decision
importance: 5
tags: [infrastructure, cost, design-principle, tokens]
source: "session"
content: "Design principle from Shael: clock cycles are cheaper than tokens by incomprehensible orders of magnitude. Every operation that can be done via script/CLI instead of LLM reasoning should be. Applies to heartbeat tasks, primitive edits, pipeline management, file operations — all of it. The belam CLI and autorun scripts are the right pattern. Continuously migrate LLM-decision work to deterministic code wherever judgment isn't genuinely needed."
status: consolidated
---

# Memory Entry

**2026-03-19T20:48:01Z** · `decision` · importance 5/5

Design principle from Shael: clock cycles are cheaper than tokens by incomprehensible orders of magnitude. Every operation that can be done via script/CLI instead of LLM reasoning should be. Applies to heartbeat tasks, primitive edits, pipeline management, file operations — all of it. The belam CLI and autorun scripts are the right pattern. Continuously migrate LLM-decision work to deterministic code wherever judgment isn't genuinely needed.

---
*Source: session*
*Tags: infrastructure, cost, design-principle, tokens*
