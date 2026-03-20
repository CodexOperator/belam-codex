---
primitive: memory_log
timestamp: "2026-03-18T18:37:16Z"
category: technical
importance: 4
tags: [infrastructure, autorun, resilience]
source: "session"
content: "Added stale session lock detection to pipeline_autorun.py. Three-tier recovery: (1) Lock staleness check every heartbeat — 5min threshold, detects dead PIDs (clear immediately) and hung processes (SIGTERM/SIGKILL/clear). Runs BEFORE gate/stall checks since stale locks block everything. (2) Gate check (existing). (3) Stall recovery at 2h (existing). New --check-locks flag for standalone use. After clearing locks, auto-resets agent sessions for clean dispatch."
status: consolidated
downstream: [memory/2026-03-19_031427_built-revision-queue-system-for-pipeline]
---

# Memory Entry

**2026-03-18T18:37:16Z** · `technical` · importance 4/5

Added stale session lock detection to pipeline_autorun.py. Three-tier recovery: (1) Lock staleness check every heartbeat — 5min threshold, detects dead PIDs (clear immediately) and hung processes (SIGTERM/SIGKILL/clear). Runs BEFORE gate/stall checks since stale locks block everything. (2) Gate check (existing). (3) Stall recovery at 2h (existing). New --check-locks flag for standalone use. After clearing locks, auto-resets agent sessions for clean dispatch.

---
*Source: session*
*Tags: infrastructure, autorun, resilience*
