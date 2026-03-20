---
primitive: memory_log
timestamp: "2026-03-17T03:34:25Z"
category: decision
importance: 4
tags: [agents, protocol, sessions-send]
source: "session"
content: "All three agents (architect, critic, builder) now use sessions_send with timeoutSeconds:0 for inter-agent communication. Session keys hardcoded in AGENT_SOUL.md and ANALYSIS_AGENT_ROLES.md. Pattern: complete stage → run pipeline_update.py → sessions_send next agent → post group chat update. No spawning new agents — use running instances."
status: consolidated
downstream: [decision/agent-session-isolation]
upstream: [decision/orchestration-architecture]
---

# Memory Entry

**2026-03-17T03:34:25Z** · `decision` · importance 4/5

All three agents (architect, critic, builder) now use sessions_send with timeoutSeconds:0 for inter-agent communication. Session keys hardcoded in AGENT_SOUL.md and ANALYSIS_AGENT_ROLES.md. Pattern: complete stage → run pipeline_update.py → sessions_send next agent → post group chat update. No spawning new agents — use running instances.

---
*Source: session*
*Tags: agents, protocol, sessions-send*
