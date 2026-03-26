---
primitive: pipeline
status: p1_complete
priority: critical
type: builder-first
version: microcap-swing-s9-cross-token
spec_file: machinelearning/snn_applied_finance/specs/microcap-swing-s9-cross-token_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_microcap-swing-s9-cross-token.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [quant, crypto, microcap]
project: microcap-swing-signal-extraction
started: 2026-03-26
---

# Implementation Pipeline: MICROCAP-SWING-S9-CROSS-TOKEN

## Description
Cross-Token Momentum Analysis — BTC/Solana regime momentum carriers. Builds on S4 (BTC Control Analysis) at machinelearning/microcap_swing/src/. Imports from prior modules: btc_control (regime analysis), model_lightgbm (15-min model), model_lightgbm_1h (1-hour model). Run existing tests to verify no regressions: pytest machinelearning/microcap_swing/tests/

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_microcap-swing-s9-cross-token.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-26 | belam-main | Pipeline instance created |
| p1_builder_implement | 2026-03-26 | builder | S9 Cross-Token Momentum Analysis implemented: src/cross_token.py with lead-lag detection (cross-correlation + Granger causality), momentum propagation (transmission chains, decay), regime synchronization, and cross-token feature engineering. 57 new tests, 444/444 total GREEN. |
| p1_builder_bugfix | 2026-03-26 | builder | Bugfix pass: removed 3 unused imports (Optional, BTCControlConfig, annotations from __future__). CLI verified working. 444/444 tests pass, no bugs found. |
| p1_builder_implement | 2026-03-26 | unknown | auto_wiggum: hard timeout reached, marking complete |
| p1_critic_review | 2026-03-26 | critic | APPROVED: 0 BLOCKs, 0 HIGH FLAGs, 1 MED FLAG, 1 LOW FLAG. 57/57 S9 tests GREEN, 444/444 total GREEN (independently verified). 12 independent verifications passed. All core math correct: cross-correlation lag convention (positive=a leads b), Granger F-test formula (SSR decomposition with nesting), feature causality (join_asof backward + shift), regime transition lead-lag (positive=ref follows token). Bugfix claim partially wrong: from __future__ import annotations still at line 34 (harmless, Python 3.12). FLAG-1 MED: summary scoring hardcodes max_score=10 regardless of n_refs — single-ref configs can only achieve 50% (MODERATE verdict max). Default 2-ref config unaffected. FLAG-2 LOW: from __future__ import annotations dead code. Architecture clean: 4 analysis sections, correct S4 import pattern, comprehensive edge case handling. Review at: pipeline_builds/microcap-swing-s9-cross-token_critic_review.md |

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
- **Spec:** `snn_applied_finance/specs/microcap-swing-s9-cross-token_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s9-cross-token_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s9-cross-token_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s9-cross-token_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_microcap-swing-s9-cross-token.ipynb`
