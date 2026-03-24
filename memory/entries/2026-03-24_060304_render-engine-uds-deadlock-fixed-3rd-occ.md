---
primitive: memory_log
timestamp: "2026-03-24T06:03:04Z"
category: technical
importance: 4
tags: [instance:main, render-engine, deadlock, fix, threading]
source: "session"
content: "Render engine UDS deadlock fixed (3rd occurrence, commit 4cac220c). Root cause: _nice_flush() called flush_change_queue() directly from UDS handler threads, competing for tree._lock with inotify/stat-poll threads. Fix: dedicated background flush worker thread as sole caller of flush_change_queue(). UDS handlers signal via threading.Event and wait with 5s timeout. Post-fix: 20/20 rapid UDS calls passed, steady at 4 threads (was 9841 before)."
status: active
---

# Memory Entry

**2026-03-24T06:03:04Z** · `technical` · importance 4/5

Render engine UDS deadlock fixed (3rd occurrence, commit 4cac220c). Root cause: _nice_flush() called flush_change_queue() directly from UDS handler threads, competing for tree._lock with inotify/stat-poll threads. Fix: dedicated background flush worker thread as sole caller of flush_change_queue(). UDS handlers signal via threading.Event and wait with 5s timeout. Post-fix: 20/20 rapid UDS calls passed, steady at 4 threads (was 9841 before).

---
*Source: session*
*Tags: instance:main, render-engine, deadlock, fix, threading*
