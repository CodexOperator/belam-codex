---
primitive: pipeline
status: p1_builder_implement
priority: critical
type: builder-first
version: microcap-swing-s7-lstm
spec_file: machinelearning/snn_applied_finance/specs/microcap-swing-s7-lstm_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_microcap-swing-s7-lstm.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [quant, crypto, microcap]
project: microcap-swing-signal-extraction
started: 2026-03-26
---

# Implementation Pipeline: MICROCAP-SWING-S7-LSTM

## Description
LSTM Secondary Model — Sequence learning for swing prediction. Builds on S3A, S3B (LightGBM 15-min and 1-hour labels) at machinelearning/microcap_swing/src/. Imports from prior modules: model_lightgbm, model_lightgbm_1h (for data loading and feature preparation), feature_engineering (feature sets). Run existing tests to verify no regressions: pytest machinelearning/microcap_swing/tests/

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_microcap-swing-s7-lstm.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-26 | belam-main | Pipeline instance created |

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
- **Spec:** `snn_applied_finance/specs/microcap-swing-s7-lstm_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s7-lstm_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s7-lstm_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s7-lstm_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_microcap-swing-s7-lstm.ipynb`
