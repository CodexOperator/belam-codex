---
primitive: memory_log
timestamp: "2026-03-18T17:08:35Z"
category: relationship
importance: 3
tags: []
source: "session"
content: "CRITICAL FIX: reset_agent_session() was resetting the wrong session. Was resetting agent:{name}:telegram:group:{id} (group session) but openclaw agent CLI uses agent:{name}:main. Fixed to reset BOTH session keys. This was why the architect processed all 3 pipelines in one session — old handoff messages were queued in the main session and never cleared. Also added session reset to checkpoint_and_resume flow."
status: consolidated
---

# Memory Entry

**2026-03-18T17:08:35Z** · `relationship` · importance 3/5

CRITICAL FIX: reset_agent_session() was resetting the wrong session. Was resetting agent:{name}:telegram:group:{id} (group session) but openclaw agent CLI uses agent:{name}:main. Fixed to reset BOTH session keys. This was why the architect processed all 3 pipelines in one session — old handoff messages were queued in the main session and never cleared. Also added session reset to checkpoint_and_resume flow.

---
*Source: session*
*Tags: none*
