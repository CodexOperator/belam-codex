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

### Pipelines
_Active implementation pipelines. Read when: checking build progress or phase gates._
- `pipelines/validate-scheme-b.md` — Implementation Pipeline: VALIDATE-SCHEME-B [local_analysis_complete/high] started:2026-03-17 [validation,statistics,snn]

### Projects
- `projects/agent-roster.md` — Active Agent Roster [active] [agents,infrastructure,roster]
- `projects/multi-agent-infrastructure.md` — Multi-Agent Infrastructure [active] [agents,infrastructure,telegram]
- `projects/quant-knowledge-skills.md` — Quant Knowledge Skills [active] [skills,knowledge,infrastructure]
- `projects/snn-applied-finance.md` — SNN Applied Finance [active] [snn,finance,crypto,trading]
- `projects/snn-standard-benchmarks.md` — SNN Standard Model Benchmarks [complete] [snn,research,benchmarking]

### Tasks
_Read when: checking open/blocked/in-pipeline work._
- `tasks/build-codex-engine.md` — Build Codex Engine [active/critical]
- `tasks/build-equilibrium-snn.md` — Build Equilibrium SNN Architecture [complete/critical]
- `tasks/build-incremental-relationship-mapper.md` — Build Incremental Relationship Mapper [active/medium] →primitive-relationship-graph
- `tasks/limit-soul-read-write.md` — Limit Soul Instance Direct Read-Write Access [open/high] →build-codex-engine
- `tasks/report-to-youtube-pipeline.md` — Build Report-to-YouTube Video Pipeline [open/high]
- `tasks/sample-task.md` — sample-task [open/medium]
- `tasks/setup-vectorbt-nautilus-pipeline.md` — Set Up Two-Phase Backtest Pipeline [open/medium] →build-equilibrium-snn
- `tasks/stack-specialist-ensemble.md` — Stack Specialist Micro-Networks [complete/high]
- `tasks/validate-scheme-b-more-folds.md` — Validate Scheme B Sharpe with 7+ Folds [in_pipeline/high]

### Decisions
_Read when: making architectural choices._
- `decisions/aad-over-finite-differences.md` — AAD Over Finite Differences for Greeks [derivatives,greeks,infrastructure]
- `decisions/agent-session-isolation.md` — Agent Session Isolation (skill:launch-pipeline) [infrastructure,agents,orchestration]
- `decisions/agent-trio-architecture.md` — Architect / Critic / Builder Agent Trio (skill:pipelines) [agents,architecture,decision]
- `decisions/belam-codex-resurrection.md` — Belam Codex Resurrection Architecture [infrastructure,git,backup]
- `decisions/clock-cycles-over-tokens.md` — Clock Cycles Over Tokens [infrastructure,cost,design-principle]
- `decisions/codex-engine-v1-architecture.md` — Codex Engine V1 Architecture [codex-engine,infrastructure,architecture]
- `decisions/derivative-specialist-skill.md` — Derivative Specialist Skill [derivatives,pricing,volatility]
- `decisions/hierarchical-memory-system.md` — Hierarchical Memory Consolidation System [infrastructure,memory-system,cron]
- `decisions/incremental-relationship-mapping-via-pairwise-opus-comparison.md` — Incremental Relationship Mapping via Pairwise Opus Compar... [infrastructure,knowledge-graph,primitives]
- `decisions/indexed-command-interface.md` — Indexed Command Interface as Default belam UX [infrastructure,cli,ux]
- `decisions/memory-as-index-not-store.md` — MEMORY.md as Boot Index, Not Knowledge Store [infrastructure,memory,primitives]
- `decisions/memory-as-primitive-type.md` — Memory Hierarchy as Primitive Type [memory,primitives,hierarchy]
- `decisions/orchestration-architecture.md` — Centralized Orchestration Architecture (skill:orchestration) [infrastructure,orchestration,agents]
- `decisions/phase2-human-gate.md` — Phase 2 Requires Explicit Human Approval [pipeline,gate,phase2]
- `decisions/population-coding-over-delta.md` — Population Coding Over Delta Encoding (Default) [encoding,snn,decision]
- `decisions/predictionmarket-specialist-skill.md` — Prediction Market Specialist Skill [prediction-markets,microstructure,market-making]
- `decisions/primitive-relationship-graph.md` — Primitive Relationship Graph [infrastructure,primitives,knowledge-graph]
- `decisions/quant-infrastructure-skill.md` — Quant Infrastructure Skill [infrastructure,backtesting,gpu]
- `decisions/quant-workflow-skill.md` — Quant Workflow Skill [methodology,statistics,overfitting]
- `decisions/skill-extraction-from-reports.md` — Extract Domain Reports Into Skills + Knowledge Files [skills,knowledge,workflow]
- `decisions/skill-primitive-pairing.md` — Every Skill Gets a Primitive [skills,primitives,conventions]
- `decisions/superseded-primitive-lifecycle.md` — Superseded Primitive Lifecycle [primitives,conventions,lifecycle]
- `decisions/supervised-builder-experiments.md` — Supervised Builder Agent for Experiment Execution [infrastructure,experiments,builder]
- `decisions/two-phase-backtest-workflow.md` — Two-Phase Backtest Workflow [backtesting,infrastructure,workflow]

### Lessons
_Read when: encountering problems or before making changes._
- `lessons/always-back-up-workspace-to-github.md` — Always Back Up Workspace to GitHub [high] [infrastructure,git,backup]
- `lessons/analysis-phase2-gate-mandatory.md` — Analysis Phase 2 is a Mandatory Gate Before New Versions [?] [pipeline,methodology,analysis]
- `lessons/beta-convergence-is-market-determined.md` — β Convergence Is Market-Determined [high] [snn,hyperparameters,convergence]
- `lessons/breakeven-accuracy-before-building.md` — Calculate Breakeven Accuracy Before Building [high] [trading,costs,validation]
- `lessons/checkpoint-and-resume-pattern.md` — Checkpoint-and-Resume for Long Agent Tasks [high] [infrastructure,agents,orchestration]
- `lessons/codex-engine-feels-native-at-v1.md` — Codex Engine Feels Native at V1 [high] [codex-engine,architecture,attention]
- `lessons/confident-abstention-is-signal.md` — Confident Abstention Is a Real Signal Type [medium] [snn,trading,abstention]
- `lessons/continuous-input-beats-spike-mode.md` — Continuous Input Mode Consistently Outperforms Spike Mode [high] [snn,encoding,input-mode]
- `lessons/control-input-dimensionality-in-encoding-comparisons.md` — Control Input Dimensionality When Comparing Encoding Schemes [high] [snn,encoding,experimental-design]
- `lessons/event-detection-not-state-classification.md` — Simple SNNs Detect Events, Not States [high] [snn,specialists,architecture]
- `lessons/gpu-parallel-thrashing-t4.md` — GPU Parallel Worker Thrashing on Tesla T4 [high] [gpu,parallelism,performance]
- `lessons/openclaw-agent-routes-to-active-session.md` — openclaw agent CLI Routes to Active Session, Not Isolated [high] [infrastructure,agents,openclaw]
- `lessons/openclaw-fixed-context-injection-list.md` — openclaw-fixed-context-injection-list [?] []
- `lessons/per-fold-significance-tests-required.md` — Per-Fold Significance Tests and Permutation Tests Are Req... [high] [methodology,statistics,validation]
- `lessons/phasic-only-ablation-wins-equilibrium.md` — Phasic-Only Ablation Wins in Equilibrium SNN [high] [snn,architecture,ablation]
- `lessons/pipeline-table-separator-required.md` — Pipeline Table Separator Required for Update Script [high] [pipeline,infrastructure,markdown]
- `lessons/scheme-b-validated-10-fold.md` — Scheme B Accuracy Validated Across 10 Folds [high] [snn,validation,scheme-b]
- `lessons/session-reset-targets-main-not-group.md` — OpenClaw Agent CLI Uses `main` Session, Not Group Session [high] [infrastructure,agents,openclaw]
- `lessons/sessions-send-timeout-filesystem-first.md` — sessions_send Timeouts — Use Filesystem-First Coordination [?] [multi-agent,coordination,sessions-send]
- `lessons/shell-splits-unquoted-list-args.md` — Shell Splits Unquoted List Arguments [high] [infrastructure,cli,debugging]
- `lessons/snn-treats-like-weird-cnn.md` — Don't Treat SNNs Like Weird CNNs [high] [snn,architecture,critical]
- `lessons/stacking-specialists-is-dead-end.md` — Stacking Specialist Micro-Networks Is a Dead End [high] [snn,ensemble,stacking]
- `lessons/subprocess-run-doesnt-raise-on-failure.md` — subprocess.run Does Not Raise on Non-Zero Exit Code [?] [python,debugging,infrastructure]
- `lessons/supermap-boot-hook-via-embed-primitives.md` — supermap-boot-hook-via-embed-primitives [?] []
- `lessons/telegram-bots-cant-see-bots.md` — Telegram Bots Cannot See Other Bots' Messages [high] [telegram,agents,infrastructure]
- `lessons/torch-buffer-requires-tensor-assignment.md` — torch.nn.Buffer Requires Tensor Assignment, Not Float [high] [snn,pytorch,debugging]
- `lessons/use-scaffold-then-edit-not-overwrite.md` — use-scaffold-then-edit-not-overwrite [high] [infrastructure,primitives,conventions]
- `lessons/verify-notebook-paths-resolve-before-automation.md` — Verify Notebook Paths Resolve Before Automation [high] [infrastructure,naming,automation]

### Commands
_`belam` CLI commands. Read when: needing usage details or flags._
- `commands/analyze-local.md` — `belam analyze-local <ver>` (belam al <ver>) — Orchestrated local analysis — data prep + architect→critic→builder loop with reasoning
- `commands/analyze.md` — `belam analyze <ver>` (belam a <ver>) — Run experiment analysis (auto-finds pipeline)
- `commands/audit.md` — `belam audit` (belam au) — Scan all primitives for consistency issues (orphaned commands, stale refs, missing decisions, duplicates)
- `commands/autorun.md` — `belam autorun` (belam auto) — Auto-kick gated/stalled/revision pipelines (event-driven)
- `commands/build.md` — `belam build <ver>` — Build a notebook version
- `commands/cleanup.md` — `belam cleanup` (belam clean) — Kill stale agent sessions (default: dry run)
- `commands/consolidate.md` — `belam consolidate` (belam cons) — Run memory consolidation
- `commands/conversations.md` — `belam conversations` (belam conv) — Export agent conversations
- `commands/create.md` — `belam create <type>` — Create a new primitive (lesson/decision/task/project/skill) with frontmatter scaffolding
- `commands/decisions.md` — `belam decisions` (belam d) — List all architectural decisions
- `commands/edges.md` — `belam edges` — 
- `commands/edit.md` — `belam edit <primitive>` — Fuzzy-match and edit primitives, --set key=value for frontmatter updates
- `commands/embed-primitives.md` — `belam embed-primitives` (belam ep) — Regenerate primitive indexes in AGENTS.md and MEMORY.md
- `commands/extract.md` — `belam extract` — 
- `commands/kickoff.md` — `belam kickoff <ver>` (belam kick) — Kick off a created pipeline (wake architect)
- `commands/knowledge-sync.md` — `belam knowledge-sync` (belam ks) — Run weekly knowledge sync
- `commands/lessons.md` — `belam lessons` (belam l) — List all lessons learned
- `commands/link.md` — `belam link <expr>...` (belam ln) — 
- `commands/log.md` — `belam log "msg"` — Quick memory entry, optionally tagged
- `commands/notebooks.md` — `belam notebooks` (belam nb) — List notebooks
- `commands/orchestrate.md` — `belam orchestrate` (belam orch) — Direct orchestrator access (complete/block/start/status/verify/revise)
- `commands/pipeline.md` — `belam pipeline <ver>` (belam p <ver>) — Detail view of a pipeline with stage history, plus update/launch/analyze subcommands
- `commands/pipelines.md` — `belam pipelines` (belam pl) — Pipeline dashboard with statuses
- `commands/projects.md` — `belam projects` (belam pj) — List all projects
- `commands/queue-revision.md` — `belam queue-revision <ver> [opts]` (belam qr) — Queue a revision request for autorun pickup
- `commands/report.md` — `belam report <ver>` — Build LaTeX→PDF report from approved analysis (orchestrated via pipeline_orchestrate.py)
- `commands/revise.md` — `belam revise <ver> --context "..."` (belam rev) — Trigger Phase 1 revision cycle (coordinator-initiated)
- `commands/run.md` — `belam run <ver>` (belam r) — Run experiments locally for a pipeline. Auto-updates stages. Builder agent fixes errors.
- `commands/status.md` — `belam status` (belam s) — Full overview: pipelines + tasks + memory + git
- `commands/task.md` — `belam task <name>` — Show one task (fuzzy match)
- `commands/tasks.md` — `belam tasks` (belam t) — List all tasks with status and priority
- `commands/transcribe.md` — `belam transcribe <file>` (belam tr) — Transcribe audio files (ogg/mp3/wav) via faster-whisper. --model tiny|base|small|medium, --json for structured output.

### Skills
_Agent skills with SKILL.md. Read when: task matches skill description._
- `skills/launch-pipeline/SKILL.md` — launch-pipeline: Launch and kick off implementation pipelines from open tasks
- `skills/orchestration/SKILL.md` — orchestration: Pipeline orchestration infrastructure — the scripts and systems that move wor...
- `skills/pipelines/SKILL.md` — pipelines: List, create, check, and archive Implementation Pipelines — the 3-phase resea...

### Knowledge
_Domain knowledge references. Read when: needing deep technical reference._
- `knowledge/derivative-specialist.md` — derivative-specialist: Derivatives pricing engineering — volatility surface construction (SVI/SSVI),... [derivatives,pricing,volatility]
- `knowledge/predictionmarket-specialist.md` — predictionmarket-specialist: Prediction market mechanics and market microstructure — LMSR cost functions, ... [prediction-markets,microstructure,market-making]
- `knowledge/quant-infrastructure.md` — quant-infrastructure: Production quant finance infrastructure — data storage, backtesting framework... [infrastructure,backtesting,gpu]
- `knowledge/quant-workflow.md` — quant-workflow: Quant research workflow — research-to-production pipeline, statistical hygien... [methodology,statistics,overfitting]

<!-- END:PRIMITIVES -->
