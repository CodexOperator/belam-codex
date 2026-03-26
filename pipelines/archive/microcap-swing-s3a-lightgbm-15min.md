---
primitive: pipeline
status: archived
priority: critical
type: builder-first
version: microcap-swing-s3a-lightgbm-15min
spec_file: machinelearning/snn_applied_finance/specs/microcap-swing-s3a-lightgbm-15min_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_microcap-swing-s3a-lightgbm-15min.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [quant, crypto, microcap]
project: microcap-swing-signal-extraction
started: 2026-03-26
archived: 2026-03-26
---

# Implementation Pipeline: MICROCAP-SWING-S3A-LIGHTGBM-15MIN

## Description
Label Construction & LightGBM — 15-min candles. Builds on S2 output at machinelearning/microcap_swing/src/features.py. Import from prior modules — do not reimplement data loading/features/etc. Run existing tests to verify no regressions: pytest machinelearning/microcap_swing/tests/

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_microcap-swing-s3a-lightgbm-15min.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-26 | belam-main | Pipeline instance created |
| p1_builder_implement | 2026-03-26 | builder | S3a implemented: src/labels.py (triple-barrier labeling: ATR-dynamic barriers, configurable TP/SL multipliers, max holding period, min ATR floor, zero-label downsampling) + src/model_lightgbm.py (walk-forward expanding-window LightGBM: purge gap=48 candles, multiclass {-1,0,+1} and binary modes, early stopping, feature importance tracking, majority baseline + directional accuracy + per-class F1 metrics, full results save). 47 new tests, 102/102 total passing. requirements.txt updated with lightgbm>=4.6.0. |
| p1_builder_bugfix | 2026-03-26 | builder | Bugfix pass (5 fixes): (1) Config mutation bug — run_walk_forward was mutating caller's LGBMConfig when binary_mode=True, now uses copy.copy(). (2) Buried import — moved Counter from inside compute_metrics() to module top-level. (3) Removed unused imports: field (both modules), save_parquet (labels.py), Optional (model_lightgbm.py). (4) Dead config fields — commented out feature_selection/min_importance_pct (declared, never used). (5) Missing column — empty-df branch in apply_triple_barrier now includes label_atr. 102/102 tests pass. |
| p1_builder_implement | 2026-03-26 | unknown | auto_wiggum: hard timeout reached, marking complete |
| p1_builder_bugfix | 2026-03-26 | builder | Re-completing after Wiggum hard-timeout duplicate dispatch. Bugfix already applied in prior session: 5 fixes (config mutation via copy.copy, Counter import moved to top-level, unused imports removed, dead config fields commented, empty-df label_atr column added). 102/102 tests passing. Critic already dispatched. |
| p1_critic_review_blocked | 2026-03-26 | critic | BLOCKED: BLOCK-1: Walk-forward split val_end formula bug. val_end = train_end + (fold+1)*segment_size grows quadratically — causes overlapping validation sets across folds (pooled metrics double-count rows) and out-of-bounds indices crash with default n_folds=5. Fix: change to val_end = min_train_rows + (fold+1)*segment_size. Also add cross-fold val overlap test. Labels module is PASS. All 5 bugfixes verified. |
| p1_builder_fix_blocks | 2026-03-26 | builder | BLOCK-1 fixed: val_end formula changed from train_end + (fold+1)*segment_size (quadratic growth, caused overlapping val sets and OOB crash at n_folds=5) to min_train_rows + (fold+1)*segment_size (linear, correct). Also: moved import copy to module top-level (FLAG-1). Added 3 new tests: cross-fold val overlap, default n_folds=5 with realistic size, val_end linear growth verification. 105/105 tests pass. |
| p1_critic_review | 2026-03-26 | critic | APPROVED: 0 BLOCKs, 0 FLAGs. BLOCK-1 fix verified correct — val_end now uses min_train_rows base (linear growth). All 5 folds produce equal-size non-overlapping val windows (152 rows each for n=1500/folds=5). No OOB indices. FLAG-1 also fixed (copy at module level). 3 new regression tests: cross-fold overlap, default config realistic size, linear growth verification. 105/105 tests GREEN. Review at: pipeline_builds/microcap-swing-s3a-lightgbm-15min_critic_review.md |

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
- **Spec:** `snn_applied_finance/specs/microcap-swing-s3a-lightgbm-15min_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s3a-lightgbm-15min_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s3a-lightgbm-15min_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s3a-lightgbm-15min_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_microcap-swing-s3a-lightgbm-15min.ipynb`
