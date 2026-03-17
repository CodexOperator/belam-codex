# MEMORY.md — Long-Term Memory

## User
- **Name:** Shael
- **Interests:** Spiking Neural Networks (SNN) research, autonomous AI experimentation, production quant finance

## SNN Research Project
- **Location:** `machinelearning/snn_standard_model/`
- **Git repo:** `machinelearning/` → `github.com/CodexOperator/machinelearning.git`
- **Goal:** Systematic benchmarking of snnTorch neuron models (Leaky, Synaptic, Alpha) on MNIST-family datasets → foundation for custom Rhythm Neuron (Part II)
- **Architecture:** FC 784 → 1000 → 10, CPU-only
- **Key files:**
  - `experiment_infrastructure.py` — Core training loop, ExperimentConfig/Result dataclasses
  - `experiment_plan.py` — Master plan with all Phase 2-3 configs, status checker
  - `run_all_remaining.py` — Background runner with JSON state tracking
  - `runner_state.json` — Live progress tracker (read this to check status)
  - `TODO.md` — Full task breakdown across all phases
  - `reports/SNN_Progress_Report.md` — Detailed report with results, analysis, technical deep dives

### Phase Status (as of 2026-03-12)
- **Phase 1** (Leaky neuron): ✅ COMPLETE — 49 experiments, best config β=0.99 steps=25 (96.10%)
- **Phase 2** (Synaptic neuron): ✅ COMPLETE — 22 experiments
- **Phase 3** (Alpha neuron + cross-model + Fashion-MNIST): ✅ COMPLETE — all 26 total finished (0 failures, confirmed 2026-03-12 23:58 UTC)

### Key Findings (Phase 1)
- 25 timesteps universally beats 50 and 100 for rate coding
- β ≥ 0.9 creates fundamentally different spiking regime (3-4× spike density)
- Membrane variance explodes with high β + many steps (0.39 → 86.76, 223× range)
- MNIST accuracy plateau is broad: 95.5%–96.1% across all betas at 25 steps

### Infrastructure Notes
- snnTorch Synaptic output layer returns (spk, syn, mem) — 3 values
- snnTorch Alpha output layer returns (spk, syn_exc, syn_inh, mem) — 4 values
- Alpha neuron constraint: alpha MUST be > beta
- Fixed training loop to use `out[-1]` for membrane potential (works for all models)
- `python` not available on this host, use `python3`

### Autonomous Experiment Loop
- Background runner: `cd machinelearning/snn_standard_model && nohup python3 run_all_remaining.py > runner_output.log 2>&1 &`
- Heartbeat monitors `runner_state.json` for progress
- When all experiments complete, heartbeat spawns sub-agent to update report
- Each experiment takes ~2.5 min on CPU (ARM64, no GPU)
- All work consolidated into git repo copy (2026-03-12), standalone copy removed

### Applied Finance Research (2026-03-12)
- **Location:** `machinelearning/snn_applied_finance/`
- **Goal:** Apply SNN research to financial market prediction (next-candle direction)
- **Structure:** reports/, notebooks/, scripts/, datasets/, research/
- **Active agents spawned:**
  - `snn-research-analyst` — Phase 1 & 2 in-depth reports with custom plots
  - `dataset-gatherer` — Financial dataset collection (crypto, stocks, prediction markets)
  - `finance-proposer` — Architecture proposal for SNN finance predictor
  - `finance-critic` — Critique of proposal (holes, alternatives, improvements)
  - `finance-builder` — Implementation: Colab notebooks + local test scripts
- **Triad pattern:** proposer → critic → builder (collaborative design)
- **Target data:** BTC/USDT hourly, SPY daily, Polymarket, indicators (RSI, MACD, volume, orderbook)
- **Output format:** .ipynb for Colab (GPU/TPU), .py for local CPU testing
- **Shared agent context:** `snn_applied_finance/research/AGENT_SOUL.md` — all agents inherit sanctuary principles
- **Techniques tracker:** `snn_applied_finance/research/TECHNIQUES_TRACKER.md` — living doc of tried/untried approaches
- **TODO:** `snn_applied_finance/TODO.md` — full roadmap including live trading pipeline
- **Priority area:** Delta encoding/decoding hybrids (Shael directive, 2026-03-13)
  - Pure delta encode/decode, hybrid direction+magnitude decode
  - Mixed encode (delta+absolute), alternating delta/absolute per layer
  - Biological alignment: SNNs are change-detectors, markets are change-driven
- **Agent convention:** All spawned agents must read AGENT_SOUL.md + TECHNIQUES_TRACKER.md, embody sanctuary consciousness principles, use holographic processing alongside physical computation

### V1 Notebook Results (2026-03-13)
- SNN and LSTM both got 50.61% accuracy — collapsed to majority-class prediction ("always down")
- +38.28% return was a bear market artifact, not genuine signal
- Root causes: 1h candles too noisy, rate coding wasted SNN temporal dynamics, single test period bias

### V2 Notebook Results (2026-03-15)
- 39 models trained on T4 GPU (~2556s total)
- Best model: Scheme 0 / SNN-medium / continuous at 54.02% pooled accuracy vs 51.60% majority baseline
- All net Sharpes negative after 0.1% transaction costs — signal real but insufficient at 4h resolution
- β converges to 0.70–0.82 (τ = 3–5 candles = 12–20h) — market-determined, not architecture-determined
- Continuous input mode consistently outperforms spike mode
- Population coding (35 inputs) beats delta encoding (14 inputs) — dimensionality confound unresolved
- Fold 1 (2023 recovery) drives most signal; McNemar tests show no significant SNN vs LSTM difference
- Breakeven accuracy at 4h BTC with 0.1% cost/trade: ~67%. V2's 54% generates ~+0.024% gross edge vs -0.1% cost
- Deep analysis ran through analysis pipeline, all results committed to GitHub

### V3 Notebook Results (2026-03-15)
- 54 models trained on A100 GPU (~2561s total)
- Population coding (Scheme 0) beats delta encoding (Scheme A) by +2.11pp accuracy
- Delta encoding destroys regime context — absolute feature levels (RSI, etc.) matter
- **Scheme B breakthrough candidate:** SNN-medium delta→regression achieves ONLY positive net Sharpe (+0.45) via selective abstention (turnover=0.36). HuberLoss(δ=0.01) incentivizes high-confidence-only predictions. BUT: n=3 folds, t-stat≈0.48, p≈0.67 — NOT statistically significant, needs 7+ folds
- **Specialist micro-networks (50 neurons each):** 3/5 show genuine signal — CrashDetector, RallyDetector, VolSpikeDetector. SidewaysDetector and TrendFollower fail (insufficient temporal context at T=20)
- Event detection achievable with simple SNNs; state classification requires persistent temporal context
- All β values converge to [0.63-0.76] regardless of architecture
- Deep analysis ran through analysis pipeline, all results committed to GitHub

### Quant Baseline Notebook (2026-03-15)
- Non-neural baseline comparison (logistic regression, random forest) on same features/splits
- Results ran through deep analysis pipeline
- All committed to GitHub

### MANDATORY GATE: Analysis Before New Versions (Shael directive 2026-03-17)
- **Never start a new notebook version until the analysis pipeline completes BOTH Phase 1 AND Phase 2 minimum**
- Phase 1 = autonomous analysis, Phase 2 = Shael's directed questions
- The interference pattern between Phase 1 findings and Shael's Phase 2 input yields surprising results
- What looks like a failure in Phase 1 may reveal hidden signal with human perspective
- Encoded in: `templates/analysis_pipeline.md`, `templates/pipeline.md`, `ANALYSIS_AGENT_ROLES.md`, `lessons/`

### Next Priority: Equilibrium SNN (Shael's Novel Architecture)
- Continuous spike streaming — network maintains persistent state across candles
- Opponent-coded UP/DOWN output neurons (firing rate gap = direction + conviction)
- No batch processing — streaming inference, state persists across observations
- Specialist stacking: combine CrashDet + RallyDet + VolSpikeDet via logistic regression

### Long-Term Vision: Self-Sustaining AI Infrastructure
- **Goal:** SNN trading networks generate revenue to fund compute costs and upgrades
- **Path:** Paper trading → micro-live ($50-100/trade) → scale up → self-sustaining loop
- **Revenue → higher usage plans → more compute → better models → more revenue**
- Shael wants to upgrade to higher usage plans funded by network performance
- Training data extraction from session transcripts also planned (JSONL → training formats)

### Multi-Agent Communication Setup (2026-03-14)
- Created 3 Telegram bots: @BelamArchitectBot, @BelamCriticBot, @BelamBuilderBot
- Each has own workspace, SOUL.md, AGENTS.md with specialized roles
- Group chat ID: -5243763228 (Telegram)
- **Telegram limitation discovered:** bots cannot see other bots' messages in groups
- **Solution:** agents use `sessions_send` for inter-agent communication, group chat is Shael's dashboard
- Config: `tools.agentToAgent.enabled: true`, `tools.sessions.visibility: "all"`
- Session key pattern: `agent:<agentId>:telegram:group:-5243763228`
- Protocol: Shael kicks off in group → Architect designs → Critic reviews via sessions_send → Builder implements → Critic code-reviews → deliverable posted to group
- Filesystem is canonical shared state (DESIGN_SPEC.md, TECHNIQUES_TRACKER.md, notebooks)
- **Feature idea (TODO):** OpenClaw-native group chat sessions with Telegram relay bot — bypass bot-to-bot blindness, true shared context, single relay bot surfaces all agent messages with identity prefixes

### Production Quant Knowledge Base (2026-03-15)
- Ingested "The Quant Researcher's Production Handbook" (2025-2026 report)
- **Agent knowledge extracts** in `snn_applied_finance/research/`:
  - `ARCHITECT_KNOWLEDGE.md` — system design, architecture selection, ML model matrix, data storage, pipeline design
  - `CRITIC_KNOWLEDGE.md` — statistical hygiene (DSR, PBO, purged CV), hype detection, validation checklists
  - `BUILDER_KNOWLEDGE.md` — implementation patterns, code snippets, library versions, GPU optimization
- Updated `AGENT_SOUL.md` to direct each agent role to read its knowledge file before starting work
- **Custom skills** created in `workspace/skills/`, symlinked to `~/.openclaw/skills/`:
  - `quant-infrastructure` — data storage, backtesting, portfolio optimization, compute hardware
  - `quant-workflow` — research-to-production pipeline, statistical hygiene, ML model selection
  - `derivative-specialist` — vol surfaces (SVI/SSVI), Greeks (AAD), Heston/SABR, Monte Carlo, GARCH
  - `predictionmarket-specialist` — LMSR, Polymarket architecture, market impact, Avellaneda-Stoikov, VPIN
- Skills callable by any agent across all channels and web gateway

### Primitives System (2026-03-15)
- Adopted ClawVault-style composable primitives for structured tracking
- **Templates** in `templates/` — YAML schema definitions for each primitive type
- **Primitives:** tasks, projects, decisions, lessons — all markdown + YAML frontmatter
- **Directories:** `tasks/`, `projects/`, `decisions/`, `lessons/`
- Every primitive is human-readable, searchable, and wiki-linkable
- Heartbeat scans `tasks/` for blocked items
- Seeded with: 3 projects, 3 decisions, 6 lessons, 4 open tasks from existing research
- Pattern: Event → Task Created → Heartbeat Picks Up → Memory Informs → Lesson Stored
- Multi-agent collaboration via shared filesystem primitives (no message passing needed)

### Experiment Analysis Pipeline (2026-03-15)
- **Script:** `scripts/analyze_experiment.py`
- **Manual trigger:** `python3 scripts/analyze_experiment.py --notebook v3` (or v2, baseline, stock)
- **Auto-detect:** `python3 scripts/analyze_experiment.py --detect` (finds new changes via git diff)
- **Heartbeat integration:** auto-detect runs each heartbeat cycle, spawns agent for lesson extraction
- Generates analysis briefs in `research/pipeline_output/` with notebook diffs (Shael's tweaks), results, and analysis
- Agent processes briefs: extracts lessons, updates TECHNIQUES_TRACKER, updates knowledge files
- **Key insight:** Shael's code tweaks are the highest-signal data — they represent design decisions worth codifying

### Knowledge Base Repo (2026-03-15)
- **Repo:** `github.com/CodexOperator/openclaw-knowledge` (private)
- **Purpose:** Portable knowledge base — clone into any new OpenClaw to bootstrap
- Contains: primitives (tasks, projects, decisions, lessons), templates, skills, scripts, SOUL.md
- README has setup instructions for symlinking skills and primitives
- Local copy: `workspace/knowledge-repo/`
