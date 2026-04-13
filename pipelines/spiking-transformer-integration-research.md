---
primitive: pipeline
status: p1_review
priority: high
type: builder-first
version: spiking-transformer-integration-research
spec_file: machinelearning/snn_applied_finance/specs/spiking-transformer-integration-research_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_spiking-transformer-integration-research.ipynb
agents: [architect, critic, builder]
supersedes: 
tags: [snn, finance]
project: snn-applied-finance
started: 2026-03-30
pending_action: p1_critic_review
current_phase: 
dispatch_claimed: false
last_updated: 2026-03-30 04:25
reset: false
---
# Implementation Pipeline: SPIKING-TRANSFORMER-INTEGRATION-RESEARCH

## Description
spiking transformer integration research

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_spiking-transformer-integration-research.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-30 | belam-main | Pipeline instance created |
| p1_builder_implement | 2026-03-30 | builder | Phase 1 implementation complete. 4 architectures built and benchmarked on SOL 1h (3-fold WF CV): LGBM baseline (0.643 acc, 1.76x lift), TabNet (0.450 acc, 1.32x lift, best ANN bull recall 0.625), Temporal CNN (0.363 acc, 0.97x lift), Dense Transformer (0.371 acc, 0.53x lift), Spiking Transformer (0.361 acc, 0.32x lift — scale fix needed). Notebook: snn_crypto_predictor_spiking-transformer-integration-research.ipynb. Results JSON saved. Phase 2 proposals: TabNet full-scale + Spiking TF beta/dm tuning + seq_len ablation. |
| p1_builder_bugfix | 2026-03-30 | builder | Root-cause bug found and fixed in SpikingTransformer. BUG: forward pass scaled input by 1/T (h=x/T) before LIF neurons — with threshold=1.0 and input std~0.33, almost no spikes fired, making Q/K all-zeros and attention degenerate. This caused bull_recall=0.003. FIX 1: Remove /T from input (pass full activation each timestep, average outputs only). FIX 2: Add BatchNorm1d before LIF Q/K projections in SpikingAttentionBlock to decouple spike rate from dm/T choices. Both fixes applied to notebook. All 24 code cells parse cleanly. Other 4 architectures unaffected. |

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
- **Spec:** `snn_applied_finance/specs/spiking-transformer-integration-research_spec.yaml`
- **Design:** `pipeline_builds/spiking-transformer-integration-research_architect_design.md`
- **Review:** `pipeline_builds/spiking-transformer-integration-research_critic_design_review.md`
- **State:** `pipeline_builds/spiking-transformer-integration-research_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_spiking-transformer-integration-research.ipynb`
