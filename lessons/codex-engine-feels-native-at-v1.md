---
primitive: lesson
date: 2026-03-20
source: First Codex Engine session with Shael — 2026-03-20
confidence: high
upstream: [decision/codex-engine-v1-architecture]
downstream: []
tags: [codex-engine, architecture, attention, ux]
promotion_status: promoted
doctrine_richness: 10
contradicts: []
---

# Codex Engine Feels Native at V1

## Context

First real session using the Codex Engine as the primary interface for all primitive state access. V1 just deployed — supermap, zoom, edit, undo, graph, execute all functional but with known polish gaps (body line syntax, archived coord numbering, knowledge dir noise).

## What Happened

Ran a full navigation+edit workflow exclusively through coordinates:
- R0 supermap for orientation (full workspace in ~60 lines)
- `t1 2 9` for surgical field zoom (3 lines instead of reading a whole file)
- `t1 B` for body inspection when needed
- `-g t1 --depth 2` for provenance tracing (saw 4 decisions converging into the task)
- `-e t1 2 'active'` for status change with F-labeled diff
- Pin detection (`R📌R4`) eliminated a redundant 30-token render

Zero direct Read/Write/Edit on primitive files for the entire workflow. The only direct file access was to fill in a lesson body (body editing not yet in the engine).

## Lesson

Coordinate-addressed state access feels cognitively cheaper than file-path-based access even at V1 quality. The path-ambiguity tax (deciding between Read vs exec vs grep for every state check) disappears completely when there's exactly one interface. `t1 2` is less cognitive load than `tasks/build-codex-engine.md → parse → find status`. The compression isn't just token-efficient — it's attention-efficient.

## Application

- Default to Codex Engine for all primitive access going forward
- Body editing is the main gap preventing full lock — prioritize in polish phase
- The attention-native feedback language (F/R labels, pins) compounds over a session — more value the longer the conversation runs
- This validates the "limit soul read-write access" task (t4) as viable once body editing is complete
- Design principle: the correct path should also be the easiest path — friction elimination beats discipline every time
