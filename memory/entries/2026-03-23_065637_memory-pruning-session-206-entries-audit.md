---
primitive: memory_log
timestamp: "2026-03-23T06:56:37Z"
category: event
importance: 3
tags: [instance:main]
source: "session"
content: "Memory pruning session: 206 entries audited, 99 pipeline stage-transition entries moved to memory/entries/_pruned/ (recoverable). Active entries reduced from 206 to 107. Root cause: consolidate_agent_memory() in pipeline_orchestrate.py was calling log_memory.py on every handoff with stage: tags. Fixed by removing indexed log_memory calls from routine completions; agent daily-file writes preserved. Also updated agent prompt templates in orchestration_engine.py and pipeline_orchestrate.py to stop instructing agents to always log memory entries."
status: active
---

# Memory Entry

**2026-03-23T06:56:37Z** · `event` · importance 3/5

Memory pruning session: 206 entries audited, 99 pipeline stage-transition entries moved to memory/entries/_pruned/ (recoverable). Active entries reduced from 206 to 107. Root cause: consolidate_agent_memory() in pipeline_orchestrate.py was calling log_memory.py on every handoff with stage: tags. Fixed by removing indexed log_memory calls from routine completions; agent daily-file writes preserved. Also updated agent prompt templates in orchestration_engine.py and pipeline_orchestrate.py to stop instructing agents to always log memory entries.

---
*Source: session*
*Tags: instance:main*
