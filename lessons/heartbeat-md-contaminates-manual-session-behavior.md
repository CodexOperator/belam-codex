---
primitive: lesson
date: 2026-03-23
source: (add source)
confidence: high
upstream: []
downstream: []
tags: [instance:main, heartbeat, lm, coordinate-grammar]
promotion_status: promoted
doctrine_richness: 6
contradicts: []
---

# heartbeat-md-contaminates-manual-session-behavior

## Context

Manual session 2026-03-23: Belam was launching Phase 2 of the codex-engine-v3-legendary-map pipeline.

## What Happened

Belam defaulted to raw `python3 scripts/pipeline_orchestrate.py` invocations instead of `e0`/`R kickoff`. Shael caught this. Investigation traced the habit to HEARTBEAT.md, which is read at every heartbeat poll and is full of raw `python3 scripts/...` invocations as the "primary" path. The agent reads HEARTBEAT.md so frequently that its patterns bleed into manual session behavior even when the coordinate grammar (LM + supermap) is fully available.

## Lesson

HEARTBEAT.md is only for heartbeat polls — its script patterns should not drive manual session behavior. In manual sessions, the supermap + LM + skills are the sole orientation layer.

## Application

- Keep HEARTBEAT.md minimal and e0/R-first; raw scripts are fallback only
- In manual sessions, never reach for a raw script when a coordinate grammar invocation exists
- When diagnosing "why did the agent bypass the LM?", check which documents it reads most frequently — those shape default behavior
