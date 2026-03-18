# MEMORY.md — Boot Index

_This is an orientation file, not a knowledge store. Details live in primitives._

## User
- **Name:** Shael
- **Style:** Autonomous workflows, proactive agents, minimal hand-holding
- **Preferences:** Check `memory_search("shael preferences")` for specifics

## Active Projects
- `projects/snn-applied-finance.md` — SNN crypto prediction research
- `projects/snn-standard-model.md` — Baseline benchmarking (COMPLETE)

## Active Pipelines
Run `belam pipelines` for live status. Pipeline files: `pipelines/*.md`

## Key Decisions
- `decisions/agent-session-isolation.md` — Fresh sessions per handoff, memory-based continuity
- `decisions/agent-trio-architecture.md` — Architect/Critic/Builder triad
- `decisions/hierarchical-memory-system.md` — Primitives-based memory
- `decisions/two-phase-backtest-workflow.md` — Phase 1 autonomous → Phase 2 human-in-the-loop

## Critical Lessons
- `lessons/session-reset-targets-main-not-group.md` — OpenClaw CLI uses `main` session
- `lessons/checkpoint-and-resume-pattern.md` — Timeout recovery pattern
- `lessons/analysis-phase2-gate-mandatory.md` — Never start new versions without analysis

## Infrastructure
- **Agents:** architect, critic, builder — all Opus, fresh sessions, auto-memory
- **Orchestrator:** `scripts/pipeline_orchestrate.py` — handoffs, memory, checkpoint-and-resume
- **Autorun:** `scripts/pipeline_autorun.py` — event-driven gate/stall automation
- **CLI:** `belam` — workspace command center (`belam status` for overview)
- **Git repo:** `machinelearning/` → `github.com/CodexOperator/machinelearning.git`

## Memory System
- **Daily logs:** `memory/YYYY-MM-DD.md` — read today + yesterday at session start
- **Indexed entries:** `memory/entries/` — searchable via `memory_search`
- **Lessons:** `lessons/*.md` — cross-agent knowledge
- **Decisions:** `decisions/*.md` — architectural choices with rationale
- **Tasks:** `tasks/*.md` — open work items
- **Consolidation:** `belam consolidate` — runs during heartbeat

## How to Orient
1. Read this file (you just did)
2. Read `memory/$(date -u +%Y-%m-%d).md` for today's context
3. Run `belam status` for live project state
4. Use `memory_search` for anything specific
5. Check primitives (`lessons/`, `decisions/`, `tasks/`) before creating new ones
