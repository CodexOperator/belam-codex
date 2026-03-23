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

## Recent Milestones (week of 2026-03-16)
- Codex Engine V3 design complete + approved (4 modules: MCP server, temporal queries, batch ops, migration)
- Orchestration V3 monitoring pipeline Phase 1 complete
- Codex Engine V2 modes pipeline Phase 1 complete
- Research-openclaw-internals and validate-scheme-b both reached local analysis complete
- All 9 pipelines touched by all 4 agents this week — full cross-agent convergence

## Infrastructure
- **Agents:** architect, critic, builder (Opus), sage (Sonnet — knowledge/extraction)
- **Orchestrator:** `scripts/pipeline_orchestrate.py` — handoffs, memory, checkpoint-and-resume
- **Autorun:** `scripts/pipeline_autorun.py` — event-driven gate/stall automation
- **Codex Engine:** `scripts/codex_engine.py` — coordinate-addressable primitive navigation
- **Memory extraction:** bootstrap hook → sage agent (automatic on /new, /reset)
- **CLI:** `belam` — workspace command center (`belam status` for overview)
- **Git repos:** workspace → `CodexOperator/belam-codex`, research → `CodexOperator/machinelearning`

## Memory System
- **Supermap:** injected at boot via hook (CODEX.codex) — coordinate-addressable view
- **Daily logs:** `memory/YYYY-MM-DD.md` — read today + yesterday at session start
- **Indexed entries:** `memory/entries/` — searchable via `memory_search`
- **Auto-extraction:** sage agent processes ended sessions → creates primitives with `instance:` tags
- **Consolidation:** `belam consolidate` — runs during heartbeat

## How to Orient
1. Read this file (you just did)
2. Read `memory/$(date -u +%Y-%m-%d).md` for today's context
3. Run `belam status` for live project state
4. Use `memory_search` for anything specific
5. Check primitives (`lessons/`, `decisions/`, `tasks/`) before creating new ones



