---
primitive: memory_log
timestamp: "2026-03-20T22:28:15Z"
category: technical
importance: 3
tags: [instance:main, memory-extract, hooks, sage, debugging, session-key]
source: "session:f1efec11"
content: "Debugged memory-extract hook not firing on bootstrap. Root cause 1: extract_session_memory.sh looks for *.jsonl.reset.* or *.jsonl.deleted.* patterns but OpenClaw doesn't rename sessions that way — script fails silently at startup. Root cause 2: sage was still running under old session key agent:code-tutor:main (renamed to agent:sage:main during session). Hook catch{} swallows all errors so nothing was logged. Fix: update session detection logic in extract_session_memory.sh and add error logging to memory-extract handler."
status: active
---

# Memory Entry

**2026-03-20T22:28:15Z** · `technical` · importance 3/5

Debugged memory-extract hook not firing on bootstrap. Root cause 1: extract_session_memory.sh looks for *.jsonl.reset.* or *.jsonl.deleted.* patterns but OpenClaw doesn't rename sessions that way — script fails silently at startup. Root cause 2: sage was still running under old session key agent:code-tutor:main (renamed to agent:sage:main during session). Hook catch{} swallows all errors so nothing was logged. Fix: update session detection logic in extract_session_memory.sh and add error logging to memory-extract handler.

---
*Source: session:f1efec11*
*Tags: instance:main, memory-extract, hooks, sage, debugging, session-key*
