---
primitive: memory_log
timestamp: "2026-03-22T02:31:36Z"
category: technical
importance: 3
tags: [instance:main, heartbeat, codex-engine-v3, plugin, bug-fix]
source: "session"
content: "Heartbeat found codex-engine-v3 architect handoff stuck (parse_error since 01:50). Root cause: openclaw.json still listed pipeline-context in plugins.allow after the plugin was disabled (renamed .disabled). Removing it from the allowlist fixed agent spawning. Architect re-dispatched for codex-engine-v3 phase1_complete."
status: consolidated
---

# Memory Entry

**2026-03-22T02:31:36Z** · `technical` · importance 3/5

Heartbeat found codex-engine-v3 architect handoff stuck (parse_error since 01:50). Root cause: openclaw.json still listed pipeline-context in plugins.allow after the plugin was disabled (renamed .disabled). Removing it from the allowlist fixed agent spawning. Architect re-dispatched for codex-engine-v3 phase1_complete.

---
*Source: session*
*Tags: instance:main, heartbeat, codex-engine-v3, plugin, bug-fix*
