---
primitive: lesson
date: 2026-03-20
status: superseded
superseded_by: (codex engine supermap-boot hook)
source: session-2a293aef
confidence: high
upstream: []
downstream: []
tags: [instance:main, codex-engine, boot-hook, supermap, infrastructure]
---

# supermap-boot-hook-via-embed-primitives

**SUPERSEDED**: The slug name is misleading. embed_primitives.py is archived.
The supermap boot hook now uses `codex_engine.py --boot` directly via `hooks/supermap-boot/handler.ts`.
The codex engine generates the coordinate-addressable primitive map at boot time.
