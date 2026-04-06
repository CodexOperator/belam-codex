---
primitive: memory_log
timestamp: "2026-03-23T11:12:20Z"
category: event
importance: 3
tags: [instance:main, pipeline, gate, concurrent]
source: "session"
content: "Pipeline gate logic updated to allow 2 concurrent pipelines instead of 1. MAX_CONCURRENT_PIPELINES=2 in pipeline_autorun.py; MAX_CONCURRENT=2 in orchestration_engine.py. kicked changed from bool to counter; get_active_agent_pipeline returns list. t6 (LM v2) and t1 (build-codex-layer-v1) now both running simultaneously."
status: consolidated
---

# Memory Entry

**2026-03-23T11:12:20Z** · `event` · importance 3/5

Pipeline gate logic updated to allow 2 concurrent pipelines instead of 1. MAX_CONCURRENT_PIPELINES=2 in pipeline_autorun.py; MAX_CONCURRENT=2 in orchestration_engine.py. kicked changed from bool to counter; get_active_agent_pipeline returns list. t6 (LM v2) and t1 (build-codex-layer-v1) now both running simultaneously.

---
*Source: session*
*Tags: instance:main, pipeline, gate, concurrent*
