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









<!-- BEGIN:PRIMITIVE_INDEX -->

## Primitive Index

lessons/ (13)
  ├─ analysis-phase2-gate-mandatory  Analysis Phase 2 is a Mandatory Gate Before New Versions  [pipeline,methodology,analysis,gate]
  ├─ beta-convergence-is-market-determined  β Convergence Is Market-Determined  high  [snn,hyperparameters,convergence]
  ├─ breakeven-accuracy-before-building  Calculate Breakeven Accuracy Before Building  high  [trading,costs,validation]
  ├─ checkpoint-and-resume-pattern  Checkpoint-and-Resume for Long Agent Tasks  high  [infrastructure,agents,orchestration,pattern]
  ├─ confident-abstention-is-signal  Confident Abstention Is a Real Signal Type  medium  [snn,trading,abstention]
  ├─ event-detection-not-state-classification  Simple SNNs Detect Events, Not States  high  [snn,specialists,architecture]
  ├─ gpu-parallel-thrashing-t4  GPU Parallel Worker Thrashing on Tesla T4  high  [gpu,parallelism,performance,colab]
  ├─ pipeline-table-separator-required  Pipeline Table Separator Required for Update Script  high  [pipeline,infrastructure,markdown,debugging]
  ├─ session-reset-targets-main-not-group  OpenClaw Agent CLI Uses `main` Session, Not Group Session  high  [infrastructure,agents,openclaw,debugging]
  ├─ sessions-send-timeout-filesystem-first  sessions_send Timeouts — Use Filesystem-First Coordination  [multi-agent,coordination,sessions-send,timeout]
  ├─ snn-treats-like-weird-cnn  Don't Treat SNNs Like Weird CNNs  high  [snn,architecture,critical]
  ├─ telegram-bots-cant-see-bots  Telegram Bots Cannot See Other Bots' Messages  high  [telegram,agents,infrastructure]
  └─ tiny-snn-gpu-parallelism  Tiny SNN Models Need Aggressive GPU Parallelism, Not Memo...  high  [gpu,parallelism,performance,infrastructure]

decisions/ (15)
  ├─ aad-over-finite-differences  AAD Over Finite Differences for Greeks  [derivatives,greeks,infrastructure]
  ├─ agent-session-isolation  Agent Session Isolation  skill:launch-pipeline  [infrastructure,agents,orchestration]
  ├─ agent-trio-architecture  Architect / Critic / Builder Agent Trio  skill:pipelines  [agents,architecture,decision]
  ├─ derivative-specialist-skill  Derivative Specialist Skill  skill:derivative-specialist  [derivatives,pricing,volatility,knowledge]
  ├─ hierarchical-memory-system  Hierarchical Memory Consolidation System  [infrastructure,memory-system,cron,knowledge-graph]
  ├─ memory-as-index-not-store  MEMORY.md as Boot Index, Not Knowledge Store  [infrastructure,memory,primitives]
  ├─ memory-as-primitive-type  Memory Hierarchy as Primitive Type  [memory,primitives,hierarchy,infrastructure]
  ├─ orchestration-architecture  Centralized Orchestration Architecture  skill:orchestration  [infrastructure,orchestration,agents,architecture]
  ├─ population-coding-over-delta  Population Coding Over Delta Encoding (Default)  [encoding,snn,decision]
  ├─ predictionmarket-specialist-skill  Prediction Market Specialist Skill  skill:predictionmarket-specialist  [prediction-markets,microstructure,market-making,knowledge]
  ├─ quant-infrastructure-skill  Quant Infrastructure Skill  skill:quant-infrastructure  [infrastructure,backtesting,gpu,data]
  ├─ quant-workflow-skill  Quant Workflow Skill  skill:quant-workflow  [methodology,statistics,overfitting,workflow]
  ├─ skill-extraction-from-reports  Extract Domain Reports Into Skills + Knowledge Files  [skills,knowledge,workflow]
  ├─ skill-primitive-pairing  Every Skill Gets a Primitive  [skills,primitives,conventions,knowledge-management]
  └─ two-phase-backtest-workflow  Two-Phase Backtest Workflow  [backtesting,infrastructure,workflow]

tasks/ (4)
  ├─ build-equilibrium-snn  Build Equilibrium SNN Architecture  in_pipeline/critical  [snn,architecture,streaming]
  ├─ setup-vectorbt-nautilus-pipeline  Set Up Two-Phase Backtest Pipeline  blocked/medium  →build-equilibrium-snn  [backtesting,infrastructure]
  ├─ stack-specialist-ensemble  Stack Specialist Micro-Networks  in_pipeline/high  [snn,ensemble,specialists]
  └─ validate-scheme-b-more-folds  Validate Scheme B Sharpe with 7+ Folds  in_pipeline/high  [validation,statistics,snn]

projects/ (5)
  ├─ agent-roster  Active Agent Roster  active  [agents,infrastructure,roster]
  ├─ multi-agent-infrastructure  Multi-Agent Infrastructure  active  [agents,infrastructure,telegram]
  ├─ quant-knowledge-skills  Quant Knowledge Skills  active  [skills,knowledge,infrastructure]
  ├─ snn-applied-finance  SNN Applied Finance  active  [snn,finance,crypto,trading]
  └─ snn-standard-benchmarks  SNN Standard Model Benchmarks  complete  [snn,research,benchmarking]

_Updated: 2026-03-18 22:49 UTC_

<!-- END:PRIMITIVE_INDEX -->
<!-- BEGIN:MEMORY_HIERARCHY -->

## Memory Hierarchy

```
Memory (2026-03-18 22:49 UTC)
├── daily/      6 active  2026-03-12 → 2026-03-19
├── entries/    48 indexed
├── weekly/
│   └─ 2026-W11  2026-03-09 → 2026-03-15  [memory]
├── monthly/    —
├── quarterly/    —
└── yearly/    —
```

<!-- END:MEMORY_HIERARCHY -->
