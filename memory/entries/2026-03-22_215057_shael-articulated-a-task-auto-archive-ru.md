---
primitive: memory_log
timestamp: "2026-03-22T21:50:57Z"
category: insight
importance: 3
tags: [instance:main, tasks, archival, pipeline]
source: "session"
content: "Shael articulated a task auto-archive rule: tasks should programmatically archive when their pipeline is archived AND either (a) the task is complete, or (b) a downstream/phase-continuation task exists and is in_pipeline or further. Discussed adding this logic to orchestration_engine.py or launch_pipeline.py. Identified 4 tasks eligible for archival: codex-engine-v2-modes-mcp-temporal, orchestration-engine-v2-temporal-autoclave, codex-engine-v3-temporal-mcp-autoclave (Phase 3 task exists), orchestration-v3-monitoring-suite (pipeline archived at phase2_complete)."
status: active
---

# Memory Entry

**2026-03-22T21:50:57Z** · `insight` · importance 3/5

Shael articulated a task auto-archive rule: tasks should programmatically archive when their pipeline is archived AND either (a) the task is complete, or (b) a downstream/phase-continuation task exists and is in_pipeline or further. Discussed adding this logic to orchestration_engine.py or launch_pipeline.py. Identified 4 tasks eligible for archival: codex-engine-v2-modes-mcp-temporal, orchestration-engine-v2-temporal-autoclave, codex-engine-v3-temporal-mcp-autoclave (Phase 3 task exists), orchestration-v3-monitoring-suite (pipeline archived at phase2_complete).

---
*Source: session*
*Tags: instance:main, tasks, archival, pipeline*
