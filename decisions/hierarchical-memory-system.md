---
primitive: decision
status: accepted
date: 2026-03-17
priority: high
tags: [infrastructure, memory-system, cron, knowledge-graph]
project: workspace-infrastructure
decided_by: [Shael, Belam]
downstream: [memory/2026-03-17_223924_built-hierarchical-memory-system-dailywe]
---

# Hierarchical Memory Consolidation System

## Decision
Implement a tiered memory consolidation system with daily → weekly → monthly → quarterly → yearly compression cascade, cross-linked to a knowledge graph wiki.

## Context
- Raw memory entries accumulate rapidly across 4 agent workspaces (main, architect, critic, builder)
- Without consolidation, older memories become unwieldy and stale
- Agents need bounded context on session startup without losing long-term knowledge
- Knowledge wiki pages need bidirectional links to memories at appropriate granularity

## Architecture
- **Daily** (00:05 UTC): Consolidate raw entries → daily log, run linker (wiki + transcripts + recent memories), run file-update checker (tasks, primitives, agent files)
- **Weekly** (Monday 03:00 UTC): Dailies → weekly with importance decay (★★★★+ full, ★★★ one-liner, below dropped) + staleness detection. Cross-link weekly ↔ daily ↔ wiki. Archive dailies >7 days. Keep 5 weekly files.
- **Monthly** (1st 04:00 UTC): Weeklies → monthly → quarterly → yearly. More aggressive decay at each level. Cross-link all levels ↔ wiki. Archive quarterlies >5. Chronological tagging throughout.

## Scripts
| Script | Purpose |
|--------|---------|
| `memory_weekly_consolidation.py` | Weekly roll-up + archival + cross-linking |
| `memory_monthly_consolidation.py` | Monthly/quarterly/yearly cascade |
| `memory_daily_linker.py` | Daily wiki + transcript + memory cross-refs |
| `memory_file_update_checker.py` | Check if primitives/scripts/agent files need updates |
| `memory_session_loader.py` | Load today + current week + current month on session start |
| `setup_memory_crons.py` | Install/update cron jobs |

## Key Design Choices
1. **Importance decay** — not everything survives. Higher consolidation levels keep less detail.
2. **Staleness detection** — resolved blockers, completed tasks, superseded decisions get flagged and don't carry forward.
3. **Rolling windows** — 7 daily, 5 weekly, 5 quarterly visible. Everything else archived (not deleted).
4. **memory/INDEX.md** — auto-generated index of all active memory files with date ranges and key topics.
5. **Serialized agents** — daily cron runs consolidation → linker → file checker sequentially to avoid race conditions.

## References
- [[memory-system-builder]] (subagent that built it)
- `knowledge/README.md` — wiki structure
- `memory/INDEX.md` — auto-generated index
