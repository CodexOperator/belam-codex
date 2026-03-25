---
primitive: lesson
date: 2026-03-25
source: session 35aad421 2026-03-25
confidence: high
upstream: [render-engine-simplification-subtract-before-build]
downstream: [codex-cockpit-v10-daemonless-direct-render]
tags: [instance:main, codex-engine, render-engine, infrastructure, simplification]
---

# render-engine-daemon-retired-script-beats-daemon

## Context

After the render engine simplification pipeline, the codex_render.py daemon had been stripped of all DiffEntry/DiffEngine/inotify functionality. Its only surviving job was receiving a UDS poke and writing supermap.txt to /dev/shm.

## What Happened

When asked how to update the supermap post-simplification, it became clear the daemon was now pure overhead: a running process, a socket, a systemd service, health checks — all to call render_supermap() and write one file per turn. Replacing it with a direct `python3 render_supermap.py` call in the cockpit plugin achieved the same result with no moving parts.

## Lesson

When a daemon is reduced to a single operation that can be done inline, retire the daemon; a script call beats a daemon.

## Application

Any time a background process is stripped of its complex functionality and only one simple synchronous job remains, consider whether a direct script call can replace it entirely. Daemons earn their keep through persistence, async handling, or multiplexing — without those, they're overhead.
