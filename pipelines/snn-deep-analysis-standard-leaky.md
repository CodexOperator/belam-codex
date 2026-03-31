---
primitive: pipeline
status: phase1_design
priority: high
type: builder-first
version: snn-deep-analysis-standard-leaky
spec_file: machinelearning/snn_applied_finance/specs/snn-deep-analysis-standard-leaky_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_snn-deep-analysis-standard-leaky.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [snn, research, analysis, standard-model]
project: snn-applied-finance
started: 2026-03-31
---

# Implementation Pipeline: SNN-DEEP-ANALYSIS-STANDARD-LEAKY

## Description
Deep analysis of standard model Leaky (LIF) neuron experiments. 51 experiments across rate/latency encoding, MNIST/FashionMNIST, beta/steps sweeps. Visualization scripts with actual experiment data. Cost function, encoding math, neuron dynamics, topology diagrams.

## Builder Instructions

**This is NOT a notebook pipeline.** The builder should:

1. **Read the task** at `tasks/snn-deep-analysis-standard-leaky.md` for full scope
2. **Read the infrastructure code** at `machinelearning/snn_standard_model/experiment_infrastructure.py` — this has the model building, encoding, training loop
3. **Read experiment results** from `machinelearning/snn_standard_model/experiments/` — JSON files with configs and results for all 51 Leaky experiments
4. **Write Python visualization scripts** in `machinelearning/snn_standard_model/research/deep_analysis/leaky_lif/`:
   - `01_rate_vs_latency_encoding_viz.py` — Same MNIST digit encoded both ways, spike timing comparison, tau effect on latency
   - `02_lif_neuron_dynamics_viz.py` — Membrane potential traces, spike generation, beta effect on decay, threshold crossing
   - `03_network_topology_viz.py` — 784→1000→10 architecture, summed membrane output (not spike count), information flow
   - `04_cost_function_viz.py` — CrossEntropyLoss on summed membrane, parameter map, what gradient descent adjusts
   - `05_experiment_results_viz.py` — Beta sweep accuracy curves, steps sweep, rate vs latency comparison, learned beta results. Load actual JSON data from experiments/
5. **Execute all scripts** — run each `.py` file, save output PNGs
6. **Compile final report** — `REPORT.md` embedding all figures with analysis

**Key constraint:** Scripts must be self-contained. Use matplotlib, numpy, torch (CPU). For experiment data, load JSONs directly from `../../experiments/`.

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
- **Spec:** `snn_applied_finance/specs/snn-deep-analysis-standard-leaky_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/snn-deep-analysis-standard-leaky_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/snn-deep-analysis-standard-leaky_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/snn-deep-analysis-standard-leaky_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_snn-deep-analysis-standard-leaky.ipynb`
