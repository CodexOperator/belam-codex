---
primitive: pipeline
status: p1_complete
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
| p1_architect_design | 2026-03-31 | architect | Design doc created with 6 script specs, report structure, data dependency confirmation, feasibility analysis, and Leaky comparison |
| p1_architect_design | 2026-03-31 | architect | Design created: 6 viz scripts spec'd for Synaptic/Alpha dual timescale analysis with cross-neuron comparison |
| p1_builder_implement | 2026-03-31 | builder | All 6 viz scripts written and executed. PNGs generated: synaptic dynamics, alpha dynamics, alpha-beta sweep heatmaps, cross-neuron comparison, dual timescale analysis, cost function convergence. REPORT.md compiled with full analysis. |
| p1_builder_bugfix | 2026-03-31 | builder | Self-review passed: all 6 scripts re-run cleanly with consistent output, all PNGs regenerated without errors, REPORT.md verified. No bugs found — clean first-pass build. |
| p1_builder_implement | 2026-03-31 | builder | All 6 viz scripts executed, PNGs generated, REPORT.md compiled |
| p1_builder_bugfix | 2026-03-31 | builder | Re-verified: all 6 scripts re-run clean, 6 PNGs regenerated, REPORT.md (136 lines) intact. No critic blocks found — no fixes needed. Artifacts ready for critic review. |
| p1_critic_review | 2026-03-31 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (cosmetic), 2 SUGGESTIONS. All 6 scripts verified — re-ran cleanly, numerical claims match output. Key findings confirmed: learnable Synaptic 97.69% dominates, fixed Alpha/Synaptic have inverted optimal regions, Leaky safest for generalization. Review written to pipeline_builds. |

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
