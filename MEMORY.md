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
