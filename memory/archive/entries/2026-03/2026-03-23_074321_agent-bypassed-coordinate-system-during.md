---
primitive: memory_log
timestamp: "2026-03-23T07:43:21Z"
category: event
importance: 3
tags: [instance:main, lm, coordinate-grammar, heartbeat, pipeline]
source: "session"
content: "Agent bypassed coordinate system during manual pipeline launch. Belam used raw script invocations (python3 scripts/pipeline_orchestrate.py) instead of e0/R-kickoff to launch Phase 2 of codex-engine-v3-legendary-map. Shael caught it. Root cause: HEARTBEAT.md and launch-pipeline SKILL.md both teach raw scripts as primary path. Both files updated in this session to use e0 and R commands as primary, scripts as fallback."
status: consolidated
---

# Memory Entry

**2026-03-23T07:43:21Z** · `event` · importance 3/5

Agent bypassed coordinate system during manual pipeline launch. Belam used raw script invocations (python3 scripts/pipeline_orchestrate.py) instead of e0/R-kickoff to launch Phase 2 of codex-engine-v3-legendary-map. Shael caught it. Root cause: HEARTBEAT.md and launch-pipeline SKILL.md both teach raw scripts as primary path. Both files updated in this session to use e0 and R commands as primary, scripts as fallback.

---
*Source: session*
*Tags: instance:main, lm, coordinate-grammar, heartbeat, pipeline*
