---
primitive: pipeline
status: phase1_design
priority: high
type: builder-first
version: snn-deep-analysis-standard-synaptic-alpha
spec_file: machinelearning/snn_applied_finance/specs/snn-deep-analysis-standard-synaptic-alpha_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_snn-deep-analysis-standard-synaptic-alpha.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [snn, research, analysis, standard-model]
project: snn-applied-finance
started: 2026-03-31
---

# Implementation Pipeline: SNN-DEEP-ANALYSIS-STANDARD-SYNAPTIC-ALPHA

## Description
Deep analysis of standard model Synaptic and Alpha neuron experiments. 41 experiments with dual decay constants (alpha+beta). Cross-neuron comparison with Leaky results. Visualization scripts with actual experiment data.

## Builder Instructions

**This is NOT a notebook pipeline.** The builder should:

1. **Read the task** at `tasks/snn-deep-analysis-standard-synaptic-alpha.md` for full scope
2. **Read the infrastructure code** at `machinelearning/snn_standard_model/experiment_infrastructure.py` — model building for Synaptic (snn.Synaptic) and Alpha (snn.Alpha) neurons
3. **Read experiment results** from `machinelearning/snn_standard_model/experiments/` — JSON files for Synaptic (syn*) and Alpha (alpha*) experiments (41 total)
4. **Write Python visualization scripts** in `machinelearning/snn_standard_model/research/deep_analysis/synaptic_alpha/`:
   - `01_synaptic_neuron_dynamics_viz.py` — Dual decay: synaptic current (alpha) → membrane potential (beta). Compare with simple Leaky LIF
   - `02_alpha_neuron_dynamics_viz.py` — Excitatory + inhibitory synaptic pathways, three state variables, richer temporal dynamics
   - `03_alpha_beta_sweep_viz.py` — Heatmaps of accuracy vs alpha/beta combinations from actual experiment JSONs
   - `04_cross_neuron_comparison_viz.py` — Leaky vs Synaptic vs Alpha accuracy comparison at matched configs, FashionMNIST transfer
   - `05_dual_timescale_viz.py` — How fast (synaptic) and slow (membrane) timescales interact, information integration over timesteps
   - `06_cost_function_viz.py` — Same CrossEntropyLoss on summed membrane, but showing how alpha/beta learning affects convergence
5. **Execute all scripts** — run each `.py` file, save output PNGs
6. **Compile final report** — `REPORT.md` embedding all figures with analysis

**Key constraint:** Scripts must be self-contained. Use matplotlib, numpy, torch (CPU). Load experiment JSONs from `../../experiments/`.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-31 | belam-main | Pipeline instance created |

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on Phase 1 completion_

### Feedback
_(Shael's feedback goes here when Phase 1 is complete and reviewed)_

## Phase 3: Iterative Research (Autonomous or Human-Triggered)
_Status: LOCKED — requires Phase 2 completion before activation_

**Gate condition:** `phase2_complete` must be set before any Phase 3 iteration can proceed.

### How Phase 3 Works

1. **Human-triggered:** Shael says "try X" → iteration created and built
2. **Agent-triggered:** Analysis reveals compelling follow-up → proposal generated:
   - Score ≥ 7: auto-approved
   - Score 4-6: flagged for Shael's review
   - Score < 4: rejected, logged only

### Iteration Log

| ID | Hypothesis | Proposed By | Status | Result |
|----|-----------|-------------|--------|--------|

## Artifacts
- **Spec:** `snn_applied_finance/specs/snn-deep-analysis-standard-synaptic-alpha_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/snn-deep-analysis-standard-synaptic-alpha_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/snn-deep-analysis-standard-synaptic-alpha_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/snn-deep-analysis-standard-synaptic-alpha_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_snn-deep-analysis-standard-synaptic-alpha.ipynb`
