---
primitive: memory_log
timestamp: "2026-03-21T16:44:34Z"
category: relationship
importance: 3
tags: [instance:main, orchestration, temporal, pipeline, hanging]
source: "session"
content: "Launched orchestration-engine-v2-temporal pipeline. Pipeline created and architect pinged via Telegram group. However, pipeline_orchestrate.py was found to use synchronous blocking 'openclaw agent --message' CLI calls (AGENT_WAKE_TIMEOUT=600s) — causes the kickoff script to hang until the agent completes its full design phase. Shael directed to investigate replacing with fire-and-forget hooks instead."
status: consolidated
---

# Memory Entry

**2026-03-21T16:44:34Z** · `relationship` · importance 3/5

Launched orchestration-engine-v2-temporal pipeline. Pipeline created and architect pinged via Telegram group. However, pipeline_orchestrate.py was found to use synchronous blocking 'openclaw agent --message' CLI calls (AGENT_WAKE_TIMEOUT=600s) — causes the kickoff script to hang until the agent completes its full design phase. Shael directed to investigate replacing with fire-and-forget hooks instead.

---
*Source: session*
*Tags: instance:main, orchestration, temporal, pipeline, hanging*
