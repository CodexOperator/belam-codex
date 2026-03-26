---
primitive: pipeline
status: p1_complete
priority: critical
type: builder-first
version: microcap-swing-s4-btc-control
spec_file: machinelearning/snn_applied_finance/specs/microcap-swing-s4-btc-control_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_microcap-swing-s4-btc-control.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [quant, crypto, microcap]
project: microcap-swing-signal-extraction
started: 2026-03-26
---

# Implementation Pipeline: MICROCAP-SWING-S4-BTC-CONTROL

## Description
S4: BTC Control Analysis. Aggregate BTC control results from S3A and S3B. Isolate meme-specific alpha: for each token, compare signal quality vs BTC baseline. Builds on S3A output at machinelearning/microcap_swing/src/lightgbm_trainer.py and S3B output at same location. Import from prior modules — do not reimplement models or data loading. Run existing tests to verify no regressions: pytest machinelearning/microcap_swing/tests/. Control analysis: BTC vs token signal cross-entropy, information coefficient, regime-dependent alpha, regime separation quality.

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_microcap-swing-s4-btc-control.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-26 | belam-main | Pipeline instance created |
| p1_builder_implement | 2026-03-26 | builder | S4 BTC Control Analysis module complete. Implemented src/btc_control.py with 6 core analysis functions: classify_btc_regimes(), compute_signal_cross_entropy(), compute_information_coefficient(), compute_regime_alpha(), compute_regime_separation(), run_btc_control_analysis(). Alpha summary scoring system (5 dimensions, 10-point max). Full test suite: 50 tests in test_btc_control.py, all passing. 203 total project tests pass with zero regressions. Module imports S3A/S3B outputs, CLI entry point at python -m src.btc_control. |
| p1_builder_bugfix | 2026-03-26 | builder | Bugfix verification complete. All imports clean, CLI entry point works (python -m src.btc_control --help), NaN guards in place for edge cases (constant-input Spearman). 203/203 tests pass. No bugs found — module is ready for code review. |
| p1_builder_implement | 2026-03-26 | unknown | auto_wiggum: hard timeout reached, marking complete |
| p1_builder_bugfix | 2026-03-26 | builder | Re-completing bugfix (auto_wiggum race condition caused duplicate dispatch). Original bugfix already verified: all imports clean, CLI works, NaN guards in place, 203/203 tests pass, no bugs found. |
| p1_critic_review | 2026-03-26 | critic | APPROVED: 0 BLOCKs, 0 HIGH FLAGs, 1 MED FLAG, 2 LOW FLAGs. 50/50 S4 tests GREEN, 203/203 total tests GREEN (independently verified). 12 independent verifications passed. All imports clean, CLI works, NaN guards functional. FLAG-1 MED: 7 unused imports from S3A/S3B modules (LGBMConfig, NON_FEATURE_COLS, compute_metrics, generate_walk_forward_splits, prepare_features, run_walk_forward, S3BConfig, run_s3b_pipeline) plus unused math — adds coupling, no runtime impact. FLAG-2 LOW: Sharpe annualization sqrt(252) vs sqrt(8760) for crypto — same issue as S3B FLAG-1, sign-preserving for alpha comparison. FLAG-3 LOW: CLI uses btc_actuals as regime proxy instead of classify_btc_regimes() since OHLCV not in prediction parquets — pragmatic but undocumented. Core math verified: cross-entropy, KL divergence, NMI, Jensen-Shannon, Spearman IC, regime alpha. Review at: pipeline_builds/microcap-swing-s4-btc-control_critic_review.md |

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
- **Spec:** `snn_applied_finance/specs/microcap-swing-s4-btc-control_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s4-btc-control_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s4-btc-control_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s4-btc-control_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_microcap-swing-s4-btc-control.ipynb`
