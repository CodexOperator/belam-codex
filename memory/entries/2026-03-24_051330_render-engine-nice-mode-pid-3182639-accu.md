---
primitive: memory_log
timestamp: "2026-03-24T05:13:30Z"
category: technical
importance: 4
tags: [instance:main, render-engine, nice-mode, threading, bug, deadlock]
source: "session"
content: "Render engine (nice mode, PID 3182639) accumulated 9841 threads and deadlocked on a futex on 2026-03-24 ~05:00 UTC. Symptom: 'supermap' UDS command timed out (0 bytes returned), cockpit plugin injected nothing into context. Root cause: thread-per-connection model — each UDS connect spawns a daemon thread; when _dispatch hangs (lock contention during _nice_flush), thread never exits. Cockpit plugin fires execFileSync each turn, creating new stuck threads per turn. Engine had 10 queued file changes unprocessed. CPU 18.9%, VSZ 83GB at time of detection."
status: active
---

# Memory Entry

**2026-03-24T05:13:30Z** · `technical` · importance 4/5

Render engine (nice mode, PID 3182639) accumulated 9841 threads and deadlocked on a futex on 2026-03-24 ~05:00 UTC. Symptom: 'supermap' UDS command timed out (0 bytes returned), cockpit plugin injected nothing into context. Root cause: thread-per-connection model — each UDS connect spawns a daemon thread; when _dispatch hangs (lock contention during _nice_flush), thread never exits. Cockpit plugin fires execFileSync each turn, creating new stuck threads per turn. Engine had 10 queued file changes unprocessed. CPU 18.9%, VSZ 83GB at time of detection.

---
*Source: session*
*Tags: instance:main, render-engine, nice-mode, threading, bug, deadlock*
