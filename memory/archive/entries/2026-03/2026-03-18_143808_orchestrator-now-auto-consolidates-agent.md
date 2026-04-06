---
primitive: memory_log
timestamp: "2026-03-18T14:38:08Z"
category: technical
importance: 3
tags: []
source: "session"
content: "Orchestrator now auto-consolidates agent memory at every handoff boundary. Added --learnings flag to complete/block commands. The script writes directly to the calling agent's memory/YYYY-MM-DD.md AND runs log_memory.py for indexed entries. Agents no longer need to manually remember to save memory — the orchestrator guarantees it happens before session ends. Also added AGENT_WORKSPACES mapping for all agent workspace paths."
status: consolidated
---

# Memory Entry

**2026-03-18T14:38:08Z** · `technical` · importance 3/5

Orchestrator now auto-consolidates agent memory at every handoff boundary. Added --learnings flag to complete/block commands. The script writes directly to the calling agent's memory/YYYY-MM-DD.md AND runs log_memory.py for indexed entries. Agents no longer need to manually remember to save memory — the orchestrator guarantees it happens before session ends. Also added AGENT_WORKSPACES mapping for all agent workspace paths.

---
*Source: session*
*Tags: none*
