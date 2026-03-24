---
primitive: task
status: open
priority: high
tags: [orchestration, infrastructure, stability]
project: workspace
created: 2026-03-24
depends_on: []
---

# Split e0 Orchestration Sweep into Focused Sub-Commands

## Problem
The monolithic `e0` sweep does everything in one pass: lock clearing, experiment monitoring, gate checking, pipeline launching, stall detection, handoff retries. This is expensive (parses all primitives + all pipeline state files) and was a major contributor to gateway freezes when triggered by heartbeat.

## Proposed Sub-Commands
- `e0 scan` — read-only status check across all pipelines, no mutations
- `e0 gates` — check gate conditions only (analysis gates, phase transitions)
- `e0 kick` — dispatch pending handoffs only
- `e0 clean` — clear stale locks and orphaned dispatches only
- `e0 stalls` — detect and report stalled pipelines (>2h no progress)
- `e0` (bare) — full sweep (all of the above, current behavior, for manual use only)

## Benefits
- Heartbeat can run `e0 scan` (cheap, read-only) and only escalate if needed
- Individual operations can be triggered on-demand without full sweep overhead
- Easier to debug which specific operation is causing issues
- Can be parallelized or run in sub-agents independently

## Implementation Notes
- Modify `scripts/codex_engine.py` e0 handler to accept sub-command argument
- Each sub-command should be independently safe (no shared state assumptions)
- `e0 scan` must be purely read-only — no file writes, no lock creation
- Consider adding `--dry-run` flag to mutation commands

## Context
- e0 was removed from HEARTBEAT.md on 2026-03-24 due to freeze issues
- Can be re-added to heartbeat once sub-commands exist (using `e0 scan` only)
- Related: renderer decoupling (completed 2026-03-24) removed another freeze source
