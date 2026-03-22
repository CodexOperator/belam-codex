---
primitive: memory_log
timestamp: "2026-03-22T21:50:42Z"
category: technical
importance: 2
tags: [instance:main, orchestration, heartbeat, sigterm]
source: "session"
content: "orchestration_engine.py keeps being killed by SIGTERM before completing — happened at both 21:02 UTC and 21:20 UTC heartbeats. Also handoff parse_errors on codex-layer-context-injection with builder and architect agents needing re-dispatch. Underlying script timeout/resource issue needs investigation."
status: consolidated
---

# Memory Entry

**2026-03-22T21:50:42Z** · `technical` · importance 2/5

orchestration_engine.py keeps being killed by SIGTERM before completing — happened at both 21:02 UTC and 21:20 UTC heartbeats. Also handoff parse_errors on codex-layer-context-injection with builder and architect agents needing re-dispatch. Underlying script timeout/resource issue needs investigation.

---
*Source: session*
*Tags: instance:main, orchestration, heartbeat, sigterm*
