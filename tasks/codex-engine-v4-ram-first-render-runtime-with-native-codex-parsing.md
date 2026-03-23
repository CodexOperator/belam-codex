---
primitive: task
status: open
priority: critical
created: 2026-03-23
owner: belam
depends_on: []
upstream: [codex-engine-v3-legendary-map, codex-engine-v3-temporal-mcp-autoclave]
downstream: []
tags: [codex-engine, v4, render-engine, ram, codex-format, infrastructure]
---

# Codex Engine v4: RAM-First Render Runtime

## Vision

The codex engine transitions from a CLI tool (read files → process → output) to a **persistent runtime** that agents live inside. The render engine (codex_render.py, 1573L from V3) becomes the single source of truth. Disk is persistence, not authority.

## Architecture

```
[Render Engine — RAM Tree (331+ nodes)]
       ↑ write          ↓ diff
   [Agent A]        [Agent B]
       ↑               ↑
   [UDS attach]    [UDS attach]
       ↓               ↓
   [Auto-flush to disk per turn]
```

### Core Principle: RAM is Truth, Disk is Persistence
- All reads come from RAM tree (no file I/O on the hot path)
- All writes go to RAM first, diff computed immediately
- Disk flush happens per-turn (normal mode) — transparent to agents
- Test mode: RAM stays isolated until explicit merge (like uncommitted git branch)
- No stale state files (render tracker, anchor, etc.) — engine memory IS the state

## Deliverables

### D1: RAM-First Write Path
- `codex_engine.py` edit operations (`e1`, `e2`, `e3`) write to render engine RAM via UDS
- Render engine computes diff immediately (no inotify round-trip)
- Auto-flush to disk after each write (fire-and-forget)
- Fallback: if engine not running, write to disk directly (graceful degradation)

### D2: Native .codex Parsing
- Render engine natively reads/writes `.codex` format (frontmatter + coordinate tree)
- CODEX.codex becomes a snapshot of the RAM tree (like a lockfile)
- Parse the existing format (~50 lines) — no format changes needed
- On engine start: load from .codex if fresher than disk scan, else rebuild

### D3: UDS Session Protocol Extensions
- `write` command: agent sends coordinate edit via UDS, engine applies to RAM
- `subscribe` command: agent registers for push notifications on changes
- `context` command: returns assembled context (scaffold + supermap + diff since attach)
- Per-session anchors: each agent has its own diff baseline (already built in V3)

### D4: Cockpit Plugin — UDS-Only Path
- `before_prompt_build` queries engine via UDS exclusively (no subprocess fallback)
- If engine is down, start it (already built) then query
- Remove all `codexExec()` subprocess calls — UDS is the only path
- Result: ~1ms context injection instead of ~300ms

### D5: .codex Stack Integration
- OpenClaw workspace discovery reads `.codex` for primitive metadata
- Bootstrap hook reads from engine (via UDS) instead of materializing from disk
- `R` CLI queries engine for all views (already partially done)
- Single source: engine → .codex snapshot → disk files (in that order)

### D6: Test Mode as Branch Semantics  
- Normal: RAM → auto-flush → disk (transparent)
- Test: RAM → hold (like uncommitted branch) → explicit commit/discard
- Both modes share the same RAM tree structure — test mode just suppresses flush
- Replaces dulwich dependency with simpler flag-based isolation

## Key Questions for Architect
1. Should the engine expose a REST-like HTTP API in addition to UDS? (for remote dashboard, canvas)
2. How does the RAM tree handle concurrent writes from 2 agents? (locking per-node vs per-namespace)
3. Should .codex snapshots be versioned (git-like) or just latest-state?
4. What happens on engine crash — rebuild from disk files or from .codex snapshot?

## Success Criteria
- [ ] Agent edit → diff visible to other attached agents in <5ms
- [ ] Zero subprocess calls in the hot path (all UDS)
- [ ] .codex file accurately reflects RAM tree state
- [ ] Engine restart recovers full state from disk in <1s
- [ ] Test mode: full session of edits, commit or discard cleanly

## D2

D2 is simplified: call existing codex_codec.py on startup to hydrate RAM tree from .codex. ~5 lines integration, not a standalone deliverable.

## D5

D5 revised: NO direct OpenClaw integration. Engine is authoritative for our agents only (via cockpit plugin UDS). Disk files remain real files that auto-flush from RAM. OpenClaw reads normal files — never needs to know about the engine. This avoids breaking other OpenClaw features that expect standard workspace files.

## D6

D6 revised: KEEP dulwich for test mode. Dulwich provides real branch semantics (merge, diff-between-branches, discard) that a simple flush-suppression flag cannot replicate. The render engine already uses dulwich — no changes needed here, just ensure it works with the RAM-first write path.
