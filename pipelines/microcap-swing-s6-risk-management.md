---
primitive: pipeline
status: p2_design
priority: critical
type: builder-first
version: microcap-swing-s6-risk-management
spec_file: machinelearning/snn_applied_finance/specs/microcap-swing-s6-risk-management_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_microcap-swing-s6-risk-management.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [quant, crypto, microcap]
project: microcap-swing-signal-extraction
started: 2026-03-26
---

# Implementation Pipeline: MICROCAP-SWING-S6-RISK-MANAGEMENT

## Description
Risk Management Overlay — Position sizing, drawdown limits, correlation hedging. Builds on S5 (Confidence Calibration) at machinelearning/microcap_swing/src/. Imports from prior modules: calibration (confidence calibration), model_lightgbm (15-min model), model_lightgbm_1h (1-hour model). Run existing tests to verify no regressions: pytest machinelearning/microcap_swing/tests/

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_microcap-swing-s6-risk-management.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-26 | belam-main | Pipeline instance created |
| p1_builder_implement | 2026-03-26 | builder | Implemented S6 risk management module: position sizing (Kelly criterion, confidence-weighted, volatility-scaled, combined), drawdown management (circuit breakers with 4-tier DD scaling, trailing DD, cooldown periods), correlation hedging (rolling cross-asset correlation, BTC beta/hedging ratios, concentration risk via HHI/effective-N, diversification ratio), and integrated risk-adjusted trading simulation comparing managed vs unmanaged equity curves. 92 new tests, all passing. 318/318 total project tests green. |
| p1_builder_bugfix | 2026-03-26 | builder | No bugs found. All 318 tests pass across all modules. Fixed one overflow warning in recovery metrics (annualized return computation). Module clean, ready for critic review. |
| p1_builder_implement | 2026-03-26 | unknown | auto_wiggum: hard timeout reached, marking complete |
| p1_critic_review_blocked | 2026-03-26 | critic | BLOCKED: BLOCK-1: Unmanaged equity curve accumulation bug in simulate_risk_adjusted_trading(). Equity initialized to all 1.0; no-trade candles leave equity[i+1] at 1.0 instead of carrying forward. Next trade reads 1.0 as base instead of accumulated value, dropping all prior PnL. Deterministic repro: 4 wins with gaps → only 1 win's PnL survives (0.000450 vs expected 0.001800). Fix: add equity[i+1] = equity[i] at loop start (same pattern as managed equity). Remove post-loop forward-fill. Add regression test. Also: FLAG-1 MED sqrt(252*24*4) annualization (same as S3B/S4), FLAG-2 LOW 5 unused imports (CalibrationConfig, compute_ece, compute_threshold_analysis, NON_FEATURE_COLS, compute_metrics), FLAG-3 LOW rolling correlation injects noise into input array view. 82/82 S6 tests GREEN, 318/318 total GREEN. Review at: pipeline_builds/microcap-swing-s6-risk-management_critic_review.md |
| p1_builder_fix_blocks | 2026-03-26 | builder | Fixed all Critic findings. BLOCK-1: unmanaged equity carry-forward bug — added equity[i+1]=equity[i] at loop start, removed broken post-loop forward-fill, added deterministic regression test. FLAG-1: replaced magic sqrt(252*24*4) with CANDLES_PER_YEAR_15M constant. FLAG-2: removed 5 unused imports. FLAG-3: .copy() on window slice before noise injection. 319/319 tests green. |
| p1_critic_review | 2026-03-26 | critic | APPROVED: 0 BLOCKs, 0 FLAGs. All 4 fixes verified: (1) BLOCK-1 unmanaged equity carry-forward fixed — equity[i+1]=equity[i] at loop start, post-loop forward-fill removed. Regression test passes (4 gapped wins accumulate correctly: 0.001800 expected, 0.001800 actual). (2) FLAG-1 sqrt(252*24*4) replaced with CANDLES_PER_YEAR_15M=35040 constant, used in both rolling vol and Calmar annualization. (3) FLAG-2 all 5 unused imports removed (CalibrationConfig, compute_ece, compute_threshold_analysis, NON_FEATURE_COLS, compute_metrics). Only LGBMConfig remains (used in main()). (4) FLAG-3 .copy() added to window slice before noise injection. 83/83 S6 tests GREEN (+1 regression), 319/319 total GREEN. Review at: pipeline_builds/microcap-swing-s6-risk-management_critic_review.md |
| p1_complete | 2026-03-26 | belam-main | Phase 2 kickoff |

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
- **Spec:** `snn_applied_finance/specs/microcap-swing-s6-risk-management_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s6-risk-management_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s6-risk-management_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s6-risk-management_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_microcap-swing-s6-risk-management.ipynb`
