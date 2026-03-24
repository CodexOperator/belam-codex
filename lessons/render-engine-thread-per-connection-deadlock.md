---
primitive: lesson
date: 2026-03-24
source: session cbf498a2 — render engine debug
confidence: high
upstream: [decision/render-engine-nice-vs-greedy-mode]
downstream: []
tags: [instance:main, render-engine, nice-mode, threading, architecture, bug]
---

# render-engine-thread-per-connection-deadlock

## Context

Investigating why the cockpit plugin was injecting an empty supermap (0 chars) into agent context. The render engine was running in nice mode (PID 3182639, started 04:47 UTC) and reported 400 tree nodes + 10 queued changes via `status` command.

## What Happened

The `supermap` UDS command timed out — never returned a response. The engine had accumulated **9841 threads** (confirmed via `/proc/<pid>/status`) and was locked on a futex. Root cause chain:

1. SessionManager uses a **thread-per-connection** model: each `accept()` spawns `threading.Thread(target=_handle_client)`.
2. In `_handle_client`, `_dispatch()` is called while holding the session lock. `_dispatch('supermap')` calls `_nice_flush()`, which calls `flush_change_queue()`, which processes file changes and writes to disk — while potentially contending with the tree's `RLock`.
3. When `_dispatch` deadlocks, the thread blocks indefinitely. The client (cockpit plugin's `execFileSync`) times out and the connection closes, but the thread remains stuck.
4. The cockpit plugin fires a **new UDS connection on every agent turn**. Each hung turn creates another stuck thread.
5. Over many turns, this produces unbounded thread accumulation → OS-level futex exhaustion → full engine lockup.

The engine was responsive to `status` early in the session (returns quickly without touching the flush path) but hung on `supermap` and `flush` commands.

## Lesson

Thread-per-connection models are unsafe when dispatch handlers can deadlock: stuck threads accumulate silently until the process becomes inoperable. In nice mode, the combination of deferred flushing + per-turn reconnects is particularly dangerous.

## Application

- Fix: use a **bounded thread pool** (e.g., `ThreadPoolExecutor`) instead of unbounded `Thread` spawning.
- Alternative: move `_nice_flush` off the locked dispatch path (flush in a background thread, dispatch reads already-flushed state).
- Monitor: add thread count to the `status` response so runaway accumulation is visible early.
- The supermap file at `/dev/shm/openclaw/supermap.txt` is a reliable fallback — cockpit plugin V7 already uses it. If UDS hangs, the plugin should fall back to the shm file immediately rather than blocking.
