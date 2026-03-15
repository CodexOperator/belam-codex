# MEMORY.md — Long-Term Memory

## User
- **Name:** Belam
- **Interests:** Spiking Neural Networks (SNN) research, autonomous AI experimentation

## SNN Research Project
- **Location:** `SNN_research/machinelearning/snn_standard_model/`
- **Git repo:** `SNN_research/machinelearning/` → `github.com/CodexOperator/machinelearning.git`
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
- **Phase 2** (Synaptic neuron): 🔄 RUNNING — 22 experiments (alpha-beta grid, learnable params, alpha→0 verification)
- **Phase 3** (Alpha neuron + cross-model + Fashion-MNIST): 🔄 QUEUED — 21 experiments

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
- Background runner: `cd SNN_research/machinelearning/snn_standard_model && nohup python3 run_all_remaining.py > runner_output.log 2>&1 &`
- Heartbeat monitors `runner_state.json` for progress
- When all experiments complete, heartbeat spawns sub-agent to update report
- Each experiment takes ~2.5 min on CPU (ARM64, no GPU)
- All work consolidated into git repo copy (2026-03-12), standalone copy removed

### Applied Finance Research (2026-03-12)
- **Location:** `SNN_research/machinelearning/snn_applied_finance/`
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
- V2 planned: delta encoding, longer candles, walk-forward validation, trio collaborative design

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
