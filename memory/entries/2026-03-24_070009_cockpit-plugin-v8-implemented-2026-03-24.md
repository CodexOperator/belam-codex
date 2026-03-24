---
primitive: memory_log
timestamp: "2026-03-24T07:00:09Z"
category: technical
importance: 4
tags: [instance:main, cockpit, render-engine, supermap, v8]
source: "session"
content: "Cockpit plugin V8 implemented 2026-03-24 ~06:59 UTC. Root cause found: hasAnchor module-level variable persists across /new sessions (gateway process stays alive), so new sessions never got supermap injection. Fix: use ctx.sessionId from before_prompt_build hook to detect session changes, plus before_reset hook to clear state on /new. V8 logic: every turn pokes engine (flush queued changes), anchor turn (new session / mtime changed / compaction) injects full supermap as CODEX R{n}, subsequent turns inject diff as CODEX Δ{n} if non-empty. Subagent (Sonnet) completed implementation in ~1 min via Ralph Wiggum pattern. Gateway restart applied at end of session."
status: active
---

# Memory Entry

**2026-03-24T07:00:09Z** · `technical` · importance 4/5

Cockpit plugin V8 implemented 2026-03-24 ~06:59 UTC. Root cause found: hasAnchor module-level variable persists across /new sessions (gateway process stays alive), so new sessions never got supermap injection. Fix: use ctx.sessionId from before_prompt_build hook to detect session changes, plus before_reset hook to clear state on /new. V8 logic: every turn pokes engine (flush queued changes), anchor turn (new session / mtime changed / compaction) injects full supermap as CODEX R{n}, subsequent turns inject diff as CODEX Δ{n} if non-empty. Subagent (Sonnet) completed implementation in ~1 min via Ralph Wiggum pattern. Gateway restart applied at end of session.

---
*Source: session*
*Tags: instance:main, cockpit, render-engine, supermap, v8*
