---
primitive: memory_log
timestamp: "2026-03-24T23:36:06Z"
category: event
importance: 3
tags: [instance:main, pipeline, orchestration, session-reset, fresh-session, spec]
source: "session"
content: "session-reset vs standard handoff spec discussed (2026-03-24): Shael asked whether pipeline templates specify when a stage transition should spawn a fresh session vs same-session handoff. Currently pipeline_orchestrate.py calls reset_agent_session() on most transitions but this is not formally specced in the builder-first-pipeline template. Shael proposed formalizing this as a spec and handing to an Opus subagent. Session ended before implementation."
status: active
---

# Memory Entry

**2026-03-24T23:36:06Z** · `event` · importance 3/5

session-reset vs standard handoff spec discussed (2026-03-24): Shael asked whether pipeline templates specify when a stage transition should spawn a fresh session vs same-session handoff. Currently pipeline_orchestrate.py calls reset_agent_session() on most transitions but this is not formally specced in the builder-first-pipeline template. Shael proposed formalizing this as a spec and handing to an Opus subagent. Session ended before implementation.

---
*Source: session*
*Tags: instance:main, pipeline, orchestration, session-reset, fresh-session, spec*
