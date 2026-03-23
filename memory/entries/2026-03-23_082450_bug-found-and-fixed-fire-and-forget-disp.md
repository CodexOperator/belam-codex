---
primitive: memory_log
timestamp: "2026-03-23T08:24:50Z"
category: technical
importance: 5
tags: [instance:main, orchestration, bug-fix, pipeline]
source: "session"
content: "BUG FOUND AND FIXED: fire_and_forget_dispatch() in orchestration_engine.py was passing '--timeout 1' to 'openclaw agent', killing every dispatched agent after 1 second. Developer incorrectly believed it controlled CLI wait time, but it sets the agent's runtime limit. Popen with start_new_session=True already returns immediately — no timeout flag needed. This was the root cause of ALL 'aborted' dispatch failures and every unclaimed_recovery since the feature was introduced. Fixed by removing '--timeout 1' (commit 724d787f). Critic was re-dispatched after fix."
status: active
---

# Memory Entry

**2026-03-23T08:24:50Z** · `technical` · importance 5/5

BUG FOUND AND FIXED: fire_and_forget_dispatch() in orchestration_engine.py was passing '--timeout 1' to 'openclaw agent', killing every dispatched agent after 1 second. Developer incorrectly believed it controlled CLI wait time, but it sets the agent's runtime limit. Popen with start_new_session=True already returns immediately — no timeout flag needed. This was the root cause of ALL 'aborted' dispatch failures and every unclaimed_recovery since the feature was introduced. Fixed by removing '--timeout 1' (commit 724d787f). Critic was re-dispatched after fix.

---
*Source: session*
*Tags: instance:main, orchestration, bug-fix, pipeline*
