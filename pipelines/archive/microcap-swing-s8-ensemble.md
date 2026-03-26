---
primitive: pipeline
status: p1_complete
priority: critical
type: builder-first
version: microcap-swing-s8-ensemble
spec_file: machinelearning/snn_applied_finance/specs/microcap-swing-s8-ensemble_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_microcap-swing-s8-ensemble.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [quant, crypto, microcap]
project: microcap-swing-signal-extraction
started: 2026-03-26
---

# Implementation Pipeline: MICROCAP-SWING-S8-ENSEMBLE

## Description
Ensemble & Meta-Learning — Stacking + Agreement Gating. Builds on S5 (Confidence Calibration) and S7 (LSTM) at machinelearning/microcap_swing/src/. Imports from prior modules: calibration, model_lstm, model_lightgbm (15-min base), model_lightgbm_1h (1-hour base). Run existing tests to verify no regressions: pytest machinelearning/microcap_swing/tests/

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_microcap-swing-s8-ensemble.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-26 | belam-main | Pipeline instance created |
| p1_builder_implement | 2026-03-26 | builder | In progress |
| p1_builder_implement | 2026-03-26 | builder | S8 Ensemble & Meta-Learning module implemented. New files: src/ensemble.py (1200+ lines) + tests/test_ensemble.py (29 tests). Components: base model collector (LightGBM + LSTM walk-forward with probability alignment), agreement gating (majority/unanimous/confidence-weighted/K-of-N), stacking meta-learner (logistic + LightGBM on stacked probabilities), combined stacking+agreement strategy. All 387 tests pass including 29 new, zero regressions. |
| p1_builder_bugfix | 2026-03-26 | builder | In progress |
| p1_builder_implement | 2026-03-26 | unknown | auto_wiggum: hard timeout reached, marking complete |
| p1_builder_bugfix | 2026-03-26 | builder | Self-review bugfix pass: (1) Fixed LSTM duplicate index issue — deduplicate by keeping last occurrence per fold. (2) Fixed 1h LightGBM model using identical config to 15m — now uses distinct hyperparams and seed for diversity. (3) Fixed stacking+agreement alignment bug — properly maps stacking val indices to gate positions via aligned index lookup. (4) Removed unused imports (copy, math) and dead code (dummy val_data in LightGBM meta, unused y_val_mapped). All 387 tests pass. |
| p1_critic_review | 2026-03-26 | critic | APPROVED: 0 BLOCKs, 0 HIGH FLAGs, 1 MED FLAG, 1 LOW FLAG. 29/29 ensemble tests GREEN, 387/387 total GREEN (independently verified). All 4 bugfix claims verified: (1) LSTM dedup keeps last occurrence per fold (correct — more training data preferred). (2) 1h LightGBM uses distinct hyperparams (num_leaves=63, max_depth=8, lr=0.03) and seed+2. (3) Stacking+agreement alignment uses aligned_idx_to_pos lookup (correct). (4) Unused imports (copy, math) and dead code removed. FLAG-1 MED: stacking_plus_agreement hardcodes min_agree=2 instead of cfg.min_agreement. FLAG-2 LOW: 3 unused imports (annotations, NON_FEATURE_COLS, SwingLSTM). Architecture clean: walk-forward everywhere, proper stacking on probabilities (not predictions), graceful degradation. Review at: pipeline_builds/microcap-swing-s8-ensemble_critic_review.md |

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
- **Spec:** `snn_applied_finance/specs/microcap-swing-s8-ensemble_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s8-ensemble_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s8-ensemble_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s8-ensemble_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_microcap-swing-s8-ensemble.ipynb`
