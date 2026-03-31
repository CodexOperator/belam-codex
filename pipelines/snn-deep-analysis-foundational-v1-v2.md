---
primitive: pipeline
status: p1_builder_implement
priority: high
type: builder-first-autogate
version: snn-deep-analysis-foundational-v1-v2
spec_file: machinelearning/snn_applied_finance/specs/snn-deep-analysis-foundational-v1-v2_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_snn-deep-analysis-foundational-v1-v2.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [snn, research, analysis, deep-dive]
project: snn-applied-finance
started: 2026-03-31
---

# Implementation Pipeline: SNN-DEEP-ANALYSIS-FOUNDATIONAL-V1-V2

## Description
Deep research analysis of foundational SNN finance notebooks (V1 stock, V1 crypto, V2). Produce executable Python scripts that generate rich visualizations of encoding/decoding, neuron communication, network topology, and cost function analysis. Compile into illustrated research report.

## Builder Instructions

**This is NOT a notebook pipeline.** The builder should:

1. **Read the reference analysis** at `machinelearning/snn_applied_finance/research/deep_analysis/01_foundational_v1_v2.md` — this contains the raw research extracted from the notebooks
2. **Read the actual source notebooks** (extract key code cells):
   - `machinelearning/llm-quant-finance/notebooks/snn_stock_predictor.ipynb`
   - `machinelearning/llm-quant-finance/notebooks/snn_crypto_predictor.ipynb`
   - `machinelearning/llm-quant-finance/notebooks/snn_crypto_predictor_v2.ipynb`
3. **Write Python visualization scripts** in `machinelearning/snn_applied_finance/research/deep_analysis/foundational_v1_v2/`:
   - `01_population_encoding_viz.py` — Gaussian tuning curves, spike raster plots, encoding→decoding round-trip
   - `02_neuron_communication_viz.py` — Membrane potential traces, spike propagation between layers, surrogate gradient shape
   - `03_network_topology_viz.py` — Architecture diagrams, parameter count comparison SNN vs LSTM
   - `04_cost_function_viz.py` — Loss landscape, what parameters change, β evolution over training
   - `05_encoding_comparison_viz.py` — Side-by-side LSTM (continuous) vs SNN (spike train) representation of the same data
4. **Execute all scripts** — run each `.py` file, save output PNGs
5. **Compile final report** — `REPORT.md` in the same directory, embedding all generated figures with analysis text

**Key constraint:** Scripts must be self-contained (no GPU required, use synthetic/example data to demonstrate the math). Use matplotlib, seaborn, numpy, torch (CPU only).

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
- **Spec:** `snn_applied_finance/specs/snn-deep-analysis-foundational-v1-v2_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/snn-deep-analysis-foundational-v1-v2_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/snn-deep-analysis-foundational-v1-v2_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/snn-deep-analysis-foundational-v1-v2_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_snn-deep-analysis-foundational-v1-v2.ipynb`
