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

lessons/ (24)  (+1 archived/superseded)
  ├─ always-back-up-workspace-to-github  Always Back Up Workspace to GitHub  high  [infrastructure,git,backup,redundancy]
  ├─ analysis-phase2-gate-mandatory  Analysis Phase 2 is a Mandatory Gate Before New Versions  [pipeline,methodology,analysis,gate]
  ├─ beta-convergence-is-market-determined  β Convergence Is Market-Determined  high  [snn,hyperparameters,convergence]
  ├─ breakeven-accuracy-before-building  Calculate Breakeven Accuracy Before Building  high  [trading,costs,validation]
  ├─ checkpoint-and-resume-pattern  Checkpoint-and-Resume for Long Agent Tasks  high  [infrastructure,agents,orchestration,pattern]
  ├─ confident-abstention-is-signal  Confident Abstention Is a Real Signal Type  medium  [snn,trading,abstention]
  ├─ continuous-input-beats-spike-mode  Continuous Input Mode Consistently Outperforms Spike Mode  high  [snn,encoding,input-mode]
  ├─ control-input-dimensionality-in-encoding-comparisons  Control Input Dimensionality When Comparing Encoding Schemes  high  [snn,encoding,experimental-design]
  ├─ event-detection-not-state-classification  Simple SNNs Detect Events, Not States  high  [snn,specialists,architecture]
  ├─ gpu-parallel-thrashing-t4  GPU Parallel Worker Thrashing on Tesla T4  high  [gpu,parallelism,performance,colab]
  ├─ per-fold-significance-tests-required  Per-Fold Significance Tests and Permutation Tests Are Req...  high  [methodology,statistics,validation]
  ├─ phasic-only-ablation-wins-equilibrium  Phasic-Only Ablation Wins in Equilibrium SNN  high  [snn,architecture,ablation,equilibrium]
  ├─ pipeline-table-separator-required  Pipeline Table Separator Required for Update Script  high  [pipeline,infrastructure,markdown,debugging]
  ├─ scheme-b-validated-10-fold  Scheme B Accuracy Validated Across 10 Folds  high  [snn,validation,scheme-b,statistics]
  ├─ session-reset-targets-main-not-group  OpenClaw Agent CLI Uses `main` Session, Not Group Session  high  [infrastructure,agents,openclaw,debugging]
  ├─ sessions-send-timeout-filesystem-first  sessions_send Timeouts — Use Filesystem-First Coordination  [multi-agent,coordination,sessions-send,timeout]
  ├─ shell-splits-unquoted-list-args  Shell Splits Unquoted List Arguments  high  [infrastructure,cli,debugging,belam]
  ├─ snn-treats-like-weird-cnn  Don't Treat SNNs Like Weird CNNs  high  [snn,architecture,critical]
  ├─ stacking-specialists-is-dead-end  Stacking Specialist Micro-Networks Is a Dead End  high  [snn,ensemble,stacking,architecture]
  ├─ subprocess-run-doesnt-raise-on-failure  subprocess.run Does Not Raise on Non-Zero Exit Code  [python,debugging,infrastructure]
  ├─ telegram-bots-cant-see-bots  Telegram Bots Cannot See Other Bots' Messages  high  [telegram,agents,infrastructure]
  ├─ torch-buffer-requires-tensor-assignment  torch.nn.Buffer Requires Tensor Assignment, Not Float  high  [snn,pytorch,debugging]
  ├─ use-scaffold-then-edit-not-overwrite  use-scaffold-then-edit-not-overwrite  high  [infrastructure,primitives,conventions,clock-cycles]
  └─ verify-notebook-paths-resolve-before-automation  Verify Notebook Paths Resolve Before Automation  high  [infrastructure,naming,automation,debugging]

decisions/ (23)
  ├─ aad-over-finite-differences  AAD Over Finite Differences for Greeks  [derivatives,greeks,infrastructure]
  ├─ agent-session-isolation  Agent Session Isolation  skill:launch-pipeline  [infrastructure,agents,orchestration]
  ├─ agent-trio-architecture  Architect / Critic / Builder Agent Trio  skill:pipelines  [agents,architecture,decision]
  ├─ belam-codex-resurrection  Belam Codex Resurrection Architecture  [infrastructure,git,backup,continuity]
  ├─ clock-cycles-over-tokens  Clock Cycles Over Tokens  [infrastructure,cost,design-principle,tokens]
  ├─ derivative-specialist-skill  Derivative Specialist Skill  [derivatives,pricing,volatility,knowledge]
  ├─ hierarchical-memory-system  Hierarchical Memory Consolidation System  [infrastructure,memory-system,cron,knowledge-graph]
  ├─ incremental-relationship-mapping-via-pairwise-opus-comparison  Incremental Relationship Mapping via Pairwise Opus Compar...  [infrastructure,knowledge-graph,primitives,relationships]
  ├─ indexed-command-interface  Indexed Command Interface as Default belam UX  [infrastructure,cli,ux,belam]
  ├─ memory-as-index-not-store  MEMORY.md as Boot Index, Not Knowledge Store  [infrastructure,memory,primitives]
  ├─ memory-as-primitive-type  Memory Hierarchy as Primitive Type  [memory,primitives,hierarchy,infrastructure]
  ├─ orchestration-architecture  Centralized Orchestration Architecture  skill:orchestration  [infrastructure,orchestration,agents,architecture]
  ├─ phase2-human-gate  Phase 2 Requires Explicit Human Approval  [pipeline,gate,phase2,infrastructure]
  ├─ population-coding-over-delta  Population Coding Over Delta Encoding (Default)  [encoding,snn,decision]
  ├─ predictionmarket-specialist-skill  Prediction Market Specialist Skill  [prediction-markets,microstructure,market-making,knowledge]
  ├─ primitive-relationship-graph  Primitive Relationship Graph  [infrastructure,primitives,knowledge-graph,conventions]
  ├─ quant-infrastructure-skill  Quant Infrastructure Skill  [infrastructure,backtesting,gpu,data]
  ├─ quant-workflow-skill  Quant Workflow Skill  [methodology,statistics,overfitting,workflow]
  ├─ skill-extraction-from-reports  Extract Domain Reports Into Skills + Knowledge Files  [skills,knowledge,workflow]
  ├─ skill-primitive-pairing  Every Skill Gets a Primitive  [skills,primitives,conventions,knowledge-management]
  ├─ superseded-primitive-lifecycle  Superseded Primitive Lifecycle  [primitives,conventions,lifecycle,boot-optimization]
  ├─ supervised-builder-experiments  Supervised Builder Agent for Experiment Execution  [infrastructure,experiments,builder,architecture]
  └─ two-phase-backtest-workflow  Two-Phase Backtest Workflow  [backtesting,infrastructure,workflow]

tasks/ (6)
  ├─ build-equilibrium-snn  Build Equilibrium SNN Architecture  complete/critical  [snn,architecture,streaming]
  ├─ build-incremental-relationship-mapper  Build Incremental Relationship Mapper  open/medium  →primitive-relationship-graph  [infrastructure,knowledge-graph,primitives,relationships]
  ├─ report-to-youtube-pipeline  Build Report-to-YouTube Video Pipeline  open/high  [video,youtube,automation,infrastructure]
  ├─ setup-vectorbt-nautilus-pipeline  Set Up Two-Phase Backtest Pipeline  open/medium  →build-equilibrium-snn  [backtesting,infrastructure]
  ├─ stack-specialist-ensemble  Stack Specialist Micro-Networks  complete/high  [snn,ensemble,specialists]
  └─ validate-scheme-b-more-folds  Validate Scheme B Sharpe with 7+ Folds  in_pipeline/high  [validation,statistics,snn]

projects/ (5)
  ├─ agent-roster  Active Agent Roster  active  [agents,infrastructure,roster]
  ├─ multi-agent-infrastructure  Multi-Agent Infrastructure  active  [agents,infrastructure,telegram]
  ├─ quant-knowledge-skills  Quant Knowledge Skills  active  [skills,knowledge,infrastructure]
  ├─ snn-applied-finance  SNN Applied Finance  active  [snn,finance,crypto,trading]
  └─ snn-standard-benchmarks  SNN Standard Model Benchmarks  complete  [snn,research,benchmarking]

pipelines/ (1)  (+4 archived/superseded)
  └─ validate-scheme-b  Implementation Pipeline: VALIDATE-SCHEME-B  local_analysis_complete/high  started:2026-03-17  [validation,statistics,snn]

commands/ (30)
  ├─ analyze-local  belam analyze-local  belam analyze-local <ver>  analysis  [analysis,local,orchestration,experiment]
  ├─ analyze  belam analyze  belam analyze <ver>  analysis  [analysis,experiment,phase2]
  ├─ audit  belam audit  belam audit  primitives  [audit,primitives,consistency,maintenance]
  ├─ autorun  belam autorun  belam autorun  pipeline  [autorun,automation,gates,stall-detection]
  ├─ build  belam build  belam build <ver>  pipeline  [build,notebook,execution]
  ├─ cleanup  belam cleanup  belam cleanup  infrastructure  [cleanup,sessions,maintenance]
  ├─ consolidate  belam consolidate  belam consolidate  memory  [memory,consolidation,maintenance]
  ├─ conversations  belam conversations  belam conversations  infrastructure  [conversations,export,agents]
  ├─ create  belam create  belam create <type>  primitives  [create,primitives,scaffolding]
  ├─ decisions  belam decisions  belam decisions  primitives  [decisions,architecture,list]
  ├─ edit  belam edit  belam edit <primitive>  primitives  [edit,primitives,fuzzy-match,frontmatter]
  ├─ embed-primitives  belam embed-primitives  belam embed-primitives  primitives  [embed,primitives,index,regenerate]
  ├─ kickoff  belam kickoff  belam kickoff <ver>  pipeline  [kickoff,pipeline,architect,launch]
  ├─ knowledge-sync  belam knowledge-sync  belam knowledge-sync  memory  [knowledge,sync,weekly,maintenance]
  ├─ lessons  belam lessons  belam lessons  primitives  [lessons,knowledge,list]
  ├─ link  belam link  belam link <expr>...  primitives  [link,relationships,primitives,graph]
  ├─ log  belam log  belam log "msg"  memory  [memory,log,quick-entry]
  ├─ notebooks  belam notebooks  belam notebooks  infrastructure  [notebooks,list]
  ├─ orchestrate  belam orchestrate  belam orchestrate  pipeline  [orchestration,direct-access,stages]
  ├─ pipeline  belam pipeline  belam pipeline <ver>  pipeline  [pipeline,detail,stages,watch]
  ├─ pipelines  belam pipelines  belam pipelines  pipeline  [pipelines,dashboard,status]
  ├─ projects  belam projects  belam projects  primitives  [projects,list,overview]
  ├─ queue-revision  belam queue-revision  belam queue-revision <ver> [opts]  pipeline  [revision,queue,autorun,pipeline]
  ├─ report  belam report  belam report <ver>  analysis  [report,latex,pdf,analysis]
  ├─ revise  belam revise  belam revise <ver> --context "..."  pipeline  [revision,phase1,architect,critic]
  ├─ run  belam run <ver>  belam run <ver>  experiment  [experiment,run,analysis,local]
  ├─ status  belam status  belam status  infrastructure  [overview,dashboard,status]
  ├─ task  belam task  belam task <name>  primitives  [task,detail,fuzzy-match]
  ├─ tasks  belam tasks  belam tasks  primitives  [tasks,list,status]
  └─ transcribe  belam transcribe <file>  belam transcribe <file>  tools

skills/ (3)
  ├─ launch-pipeline  launch-pipeline  Launch and kick off implementation pipelines fr...
  ├─ orchestration  orchestration  Pipeline orchestration infrastructure — the scr...
  └─ pipelines  pipelines  List, create, check, and archive Implementation...

knowledge/ (4)
  ├─ derivative-specialist  derivative-specialist  Derivatives pricing engineering — volatility su...  [derivatives,pricing,volatility,greeks]
  ├─ predictionmarket-specialist  predictionmarket-specialist  Prediction market mechanics and market microstr...  [prediction-markets,microstructure,market-making,lmsr]
  ├─ quant-infrastructure  quant-infrastructure  Production quant finance infrastructure — data ...  [infrastructure,backtesting,gpu,data]
  └─ quant-workflow  quant-workflow  Quant research workflow — research-to-productio...  [methodology,statistics,overfitting,workflow]

_Updated: 2026-03-20 05:13 UTC_

<!-- END:PRIMITIVE_INDEX -->
<!-- BEGIN:MEMORY_HIERARCHY -->

## Memory Hierarchy

```
Memory (2026-03-20 05:13 UTC)
├── daily/      7 active  2026-03-15 → 2026-03-21
├── entries/    82 indexed
├── weekly/
│   └─ 2026-W11  2026-03-09 → 2026-03-15  [memory]
├── monthly/    —
├── quarterly/    —
└── yearly/    —
```

<!-- END:MEMORY_HIERARCHY -->
