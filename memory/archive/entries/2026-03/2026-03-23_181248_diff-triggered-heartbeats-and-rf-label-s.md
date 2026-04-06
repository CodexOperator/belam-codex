---
primitive: memory_log
timestamp: "2026-03-23T18:12:48Z"
category: event
importance: 4
tags: [instance:main, render-engine, diff, heartbeat, architecture]
source: "session"
content: "Diff-triggered heartbeats and R/F label split implemented. HeartbeatTrigger thread added to codex_render.py: polls every 5s, fires POST to /hooks/wake when 10+ F-label diffs accumulate. Coordinator (main) gets R-only diffs; pipeline agents get R+F. DiffEntry.content field added. Cockpit plugin updated with include_content by agent role. Webhook hooks endpoint enabled. Committed ceb8d260 to belam-codex."
status: consolidated
---

# Memory Entry

**2026-03-23T18:12:48Z** · `event` · importance 4/5

Diff-triggered heartbeats and R/F label split implemented. HeartbeatTrigger thread added to codex_render.py: polls every 5s, fires POST to /hooks/wake when 10+ F-label diffs accumulate. Coordinator (main) gets R-only diffs; pipeline agents get R+F. DiffEntry.content field added. Cockpit plugin updated with include_content by agent role. Webhook hooks endpoint enabled. Committed ceb8d260 to belam-codex.

---
*Source: session*
*Tags: instance:main, render-engine, diff, heartbeat, architecture*
