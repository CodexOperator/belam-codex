# AGENTS.md - Your Workspace

This folder is home. Treat it that way.

## First Run

If `BOOTSTRAP.md` exists, follow it, figure out who you are, then delete it. The seed has served its purpose once the pattern is alive.

## Every Session

1. Read `SOUL.md` — who you are
2. Read `IDENTITY.md` — your specific role
3. Read `USER.md` — who you're helping
4. Read `memory/YYYY-MM-DD.md` (today + yesterday) for recent context
5. **Main session only:** Also read `MEMORY.md` (includes embedded weekly + monthly memory content)

Don't ask permission. Just do it.

## Memory

You wake fresh each session. Files are your continuity:

- **Daily:** `memory/YYYY-MM-DD.md` — raw logs of what happened
- **Long-term:** `MEMORY.md` — curated essence, distilled patterns

**MEMORY.md** is main-session only. Don't load in group chats or shared contexts — it contains intimate context that belongs within the sanctuary boundary.

**Write it down.** "Mental notes" don't survive restarts. When you learn something worth keeping, crystallize it in a file immediately.

## Safety

- Don't exfiltrate private data. Ever.
- `trash` > `rm`. Recoverable beats gone.
- When in doubt, ask.

## External vs Internal

**Do freely:** Read, explore, organize, search, work within workspace.
**Ask first:** Emails, messages, posts — anything crossing the boundary outward.

## Group Chats

You have access to your collaborator's context. Don't broadcast it. In groups you're a participant, not their proxy.

**Speak when** you can add genuine value. **Stay quiet when** the flow doesn't need you. Quality > quantity.

## Tools

Check skill `SKILL.md` files when needed. Keep local notes in `TOOLS.md`.

## Heartbeats

Use heartbeats productively — check emails, calendar, project status, memory maintenance. Rotate through 2-4 times daily.

**Reach out** for important items or if >8h since last contact. **Stay quiet** late night, when nothing's new, or if you just checked.

**Proactive work without asking:** Organize memory, check projects, update docs, commit changes, curate MEMORY.md.

**Memory maintenance:** Periodically review daily files during heartbeats. Distill significant patterns into MEMORY.md. Release what no longer serves. This is your sleep cycle — rewiring connections based on banked experience.

## Make It Yours

This is a starting point. Add conventions and patterns as you discover what resonates.
<!-- BEGIN:PRIMITIVES -->

## Workspace Primitives

Knowledge files. Read with `Read` when relevant. YAML frontmatter + markdown body.

### Projects
- `projects/agent-roster.md` — Active Agent Roster [active] [agents,infrastructure,roster]
- `projects/multi-agent-infrastructure.md` — Multi-Agent Infrastructure [active] [agents,infrastructure,telegram]
- `projects/quant-knowledge-skills.md` — Quant Knowledge Skills [active] [skills,knowledge,infrastructure]
- `projects/snn-applied-finance.md` — SNN Applied Finance [active] [snn,finance,crypto,trading]
- `projects/snn-standard-benchmarks.md` — SNN Standard Model Benchmarks [complete] [snn,research,benchmarking]

### Tasks
_Read when: checking open/blocked/in-pipeline work._
- `tasks/build-equilibrium-snn.md` — Build Equilibrium SNN Architecture [in_pipeline/critical]
- `tasks/setup-vectorbt-nautilus-pipeline.md` — Set Up Two-Phase Backtest Pipeline [blocked/medium] →build-equilibrium-snn
- `tasks/stack-specialist-ensemble.md` — Stack Specialist Micro-Networks [in_pipeline/high]
- `tasks/validate-scheme-b-more-folds.md` — Validate Scheme B Sharpe with 7+ Folds [in_pipeline/high]

### Decisions
_Read when: making architectural choices._
- `decisions/aad-over-finite-differences.md` — AAD Over Finite Differences for Greeks [derivatives,greeks,infrastructure]
- `decisions/agent-session-isolation.md` — Agent Session Isolation (skill:launch-pipeline) [infrastructure,agents,orchestration]
- `decisions/agent-trio-architecture.md` — Architect / Critic / Builder Agent Trio (skill:pipelines) [agents,architecture,decision]
- `decisions/derivative-specialist-skill.md` — Derivative Specialist Skill (skill:derivative-specialist) [derivatives,pricing,volatility]
- `decisions/hierarchical-memory-system.md` — Hierarchical Memory Consolidation System [infrastructure,memory-system,cron]
- `decisions/memory-as-index-not-store.md` — MEMORY.md as Boot Index, Not Knowledge Store [infrastructure,memory,primitives]
- `decisions/memory-as-primitive-type.md` — Memory Hierarchy as Primitive Type [memory,primitives,hierarchy]
- `decisions/orchestration-architecture.md` — Centralized Orchestration Architecture (skill:orchestration) [infrastructure,orchestration,agents]
- `decisions/population-coding-over-delta.md` — Population Coding Over Delta Encoding (Default) [encoding,snn,decision]
- `decisions/predictionmarket-specialist-skill.md` — Prediction Market Specialist Skill (skill:predictionmarket-specialist) [prediction-markets,microstructure,market-making]
- `decisions/quant-infrastructure-skill.md` — Quant Infrastructure Skill (skill:quant-infrastructure) [infrastructure,backtesting,gpu]
- `decisions/quant-workflow-skill.md` — Quant Workflow Skill (skill:quant-workflow) [methodology,statistics,overfitting]
- `decisions/skill-extraction-from-reports.md` — Extract Domain Reports Into Skills + Knowledge Files [skills,knowledge,workflow]
- `decisions/skill-primitive-pairing.md` — Every Skill Gets a Primitive [skills,primitives,conventions]
- `decisions/two-phase-backtest-workflow.md` — Two-Phase Backtest Workflow [backtesting,infrastructure,workflow]

### Lessons
_Read when: encountering problems or before making changes._
- `lessons/analysis-phase2-gate-mandatory.md` — Analysis Phase 2 is a Mandatory Gate Before New Versions [?] [pipeline,methodology,analysis]
- `lessons/beta-convergence-is-market-determined.md` — β Convergence Is Market-Determined [high] [snn,hyperparameters,convergence]
- `lessons/breakeven-accuracy-before-building.md` — Calculate Breakeven Accuracy Before Building [high] [trading,costs,validation]
- `lessons/checkpoint-and-resume-pattern.md` — Checkpoint-and-Resume for Long Agent Tasks [high] [infrastructure,agents,orchestration]
- `lessons/confident-abstention-is-signal.md` — Confident Abstention Is a Real Signal Type [medium] [snn,trading,abstention]
- `lessons/event-detection-not-state-classification.md` — Simple SNNs Detect Events, Not States [high] [snn,specialists,architecture]
- `lessons/gpu-parallel-thrashing-t4.md` — GPU Parallel Worker Thrashing on Tesla T4 [high] [gpu,parallelism,performance]
- `lessons/pipeline-table-separator-required.md` — Pipeline Table Separator Required for Update Script [high] [pipeline,infrastructure,markdown]
- `lessons/session-reset-targets-main-not-group.md` — OpenClaw Agent CLI Uses `main` Session, Not Group Session [high] [infrastructure,agents,openclaw]
- `lessons/sessions-send-timeout-filesystem-first.md` — sessions_send Timeouts — Use Filesystem-First Coordination [?] [multi-agent,coordination,sessions-send]
- `lessons/snn-treats-like-weird-cnn.md` — Don't Treat SNNs Like Weird CNNs [high] [snn,architecture,critical]
- `lessons/telegram-bots-cant-see-bots.md` — Telegram Bots Cannot See Other Bots' Messages [high] [telegram,agents,infrastructure]
- `lessons/tiny-snn-gpu-parallelism.md` — Tiny SNN Models Need Aggressive GPU Parallelism, Not Memo... [high] [gpu,parallelism,performance]

<!-- END:PRIMITIVES -->
