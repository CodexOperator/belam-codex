---
primitive: lesson
date: 2026-03-24
source: session cbf498a2 — render engine debug
confidence: high
upstream: [decision/render-engine-nice-vs-greedy-mode]
downstream: []
tags: [instance:main, render-engine, nice-mode, bug, locking]
promotion_status: promoted
doctrine_richness: 10
contradicts: []
---

# nice-mode-flush-supermap-command-ordering

## Context

The render engine's nice mode defers all file change processing until an explicit query. The `supermap` UDS command is supposed to trigger a flush before rendering, ensuring the returned supermap is current.

## What Happened

Code analysis confirmed the ordering:
```
supermap cmd → _nice_flush() → flush_change_queue() → _process_file_change() × N → render_supermap()
```

`_nice_flush` calls `_engine_ref.flush_change_queue()`, which pops from `_change_queue` and calls `_process_file_change`. That function calls `tree.apply_disk_change()` and `diff_engine.record()`, both of which acquire the tree's `RLock`. If the session dispatch thread already holds the lock (or another thread does), this deadlocks.

Additionally, `flush_change_queue` also calls `self._write_supermap_file()` after processing — writing to disk while potentially under lock pressure.

The `/dev/shm/openclaw/supermap.txt` file written at engine startup (04:47 UTC) was valid and readable, but the UDS `supermap` command path was broken.

## Lesson

The nice-mode design has a hidden ordering hazard: the flush that makes the supermap current is also the thing most likely to deadlock, because it runs file I/O and tree mutations on the same thread that's handling the UDS request — which may already be holding locks.

## Application

- The shm file (`/dev/shm/openclaw/supermap.txt`) written at startup is the reliable fallback — it's always at least as fresh as boot time.
- Cockpit plugin should read the shm file directly as primary path (V7 already does this on subsequent turns via mtime check). On first turn, if UDS query times out, fall back to shm file immediately.
- Longer term: flush should happen in a dedicated background thread that is never on the UDS dispatch path.
