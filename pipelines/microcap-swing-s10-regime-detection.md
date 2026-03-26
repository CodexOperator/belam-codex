---
primitive: pipeline
status: p1_complete
priority: critical
type: builder-first
version: microcap-swing-s10-regime-detection
spec_file: machinelearning/snn_applied_finance/specs/microcap-swing-s10-regime-detection_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_microcap-swing-s10-regime-detection.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [quant, crypto, microcap]
project: microcap-swing-signal-extraction
started: 2026-03-26
---

# Implementation Pipeline: MICROCAP-SWING-S10-REGIME-DETECTION

## Description
Regime Detection Pre-Filter — Market regime classification (bull/chop/bear) as entry/exit constraint. Builds on S4 (BTC Control) and S5 (Confidence Calibration) at machinelearning/microcap_swing/src/. Imports from prior modules: btc_control (regime classification), calibration (confidence calibration), model_lightgbm (15-min model). Run existing tests to verify no regressions: pytest machinelearning/microcap_swing/tests/

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_microcap-swing-s10-regime-detection.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-26 | belam-main | Pipeline instance created |
| p1_builder_implement | 2026-03-26 | unknown | auto_wiggum: hard timeout reached, marking complete |
| p1_builder_bugfix | 2026-03-26 | builder | S10 regime_detection.py verified clean — 67 dedicated tests, 511 full suite pass, zero regressions. Implementation covers: (1) volatility regime via rolling vol z-score, (2) trend regime via dual-MA + ADX, (3) composite regime with BTC confirmation, (4) self-contained Gaussian HMM (Baum-Welch + Viterbi, no hmmlearn dependency), (5) regime gating with cooldown + confidence filtering, (6) walk-forward evaluation comparing filtered vs unfiltered performance. Integration smoke test confirms all methods produce valid regime distributions. |
| p1_critic_review | 2026-03-26 | critic | APPROVED: 0 BLOCKs, 0 HIGH FLAGs, 1 MED FLAG, 1 LOW FLAG. 67/67 S10 tests GREEN, 511/511 total GREEN (independently verified). 12 independent verifications passed. Self-contained Gaussian HMM (Baum-Welch + Viterbi, log-space, Cholesky + diagonal fallback) verified correct — probabilities sum to 1.0, states sorted by mean return. Walk-forward splits use linear val_end (min_train base), no cross-fold overlap, 48-candle purge gaps. All 4 regime classifiers (vol, trend, composite, HMM) verified causal (backward-looking rolling ops). Gating direction filtering correct (bull+long=pass, bull+short=block, etc.). Cooldown and confidence suppression work correctly. FLAG-1 MED: BTCControlConfig imported but unused (same pattern as S4-S8). FLAG-2 LOW: df_train computed but unused for non-HMM methods. Review at: pipeline_builds/microcap-swing-s10-regime-detection_critic_review.md |

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
- **Spec:** `snn_applied_finance/specs/microcap-swing-s10-regime-detection_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s10-regime-detection_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s10-regime-detection_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s10-regime-detection_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_microcap-swing-s10-regime-detection.ipynb`
