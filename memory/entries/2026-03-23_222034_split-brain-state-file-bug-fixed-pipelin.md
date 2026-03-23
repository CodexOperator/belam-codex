---
primitive: memory_log
timestamp: "2026-03-23T22:20:34Z"
category: technical
importance: 4
tags: [instance:main, bug, pipeline, state-file]
source: "session"
content: "Split-brain state file bug fixed: pipeline_update.py wrote to flat {version}_state.json while sweep's load_state_json() preferred {version}/_state.json (subdirectory). Caused p2 (limbic-reward-snn) to show phase1_complete in sweep despite experiment being fully done. Fix: save_state() now writes both paths; load_state() checks subdirectory first."
status: consolidated
---

# Memory Entry

**2026-03-23T22:20:34Z** · `technical` · importance 4/5

Split-brain state file bug fixed: pipeline_update.py wrote to flat {version}_state.json while sweep's load_state_json() preferred {version}/_state.json (subdirectory). Caused p2 (limbic-reward-snn) to show phase1_complete in sweep despite experiment being fully done. Fix: save_state() now writes both paths; load_state() checks subdirectory first.

---
*Source: session*
*Tags: instance:main, bug, pipeline, state-file*
