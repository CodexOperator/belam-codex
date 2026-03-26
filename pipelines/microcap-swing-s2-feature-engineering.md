---
primitive: pipeline
status: archived
priority: critical
type: builder-first
version: microcap-swing-s2-feature-engineering
spec_file: machinelearning/snn_applied_finance/specs/microcap-swing-s2-feature-engineering_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_microcap-swing-s2-feature-engineering.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [quant, crypto, microcap, feature-engineering]
project: microcap-swing-signal-extraction
started: 2026-03-26
archived: 2026-03-26
---

# Implementation Pipeline: MICROCAP-SWING-S2-FEATURE-ENGINEERING

## Description
S2: Feature Engineering — Technical + Sentiment + Cross-Asset + Temporal features. Builds on S1 output at machinelearning/microcap_swing/src/data_pipeline.py. Import from prior modules — do not reimplement data loading. Multi-timeframe aggregation (5-min through daily), volume-centric features, RSI/Bollinger/MACD, Fear & Greed interaction features, cross-asset features (BTC/SOL returns, correlations). See tasks/microcap-swing-signal-extraction.md S2 for full spec. Run tests to verify no regressions: pytest machinelearning/microcap_swing/tests/

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_microcap-swing-s2-feature-engineering.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-26 | belam-main | Pipeline instance created |
| p1_builder_implement | 2026-03-26 | builder | S2 Feature Engineering complete: src/features.py implements all 7 feature categories from spec (volume-centric, momentum, trend, MTF aggregation, sentiment/F&G, cross-asset, temporal). 30 new tests all pass. 55 total tests (S1+S2) pass with zero regressions. CLI: python -m src.features --token BONK --timeframe 15m |
| p1_builder_bugfix | 2026-03-26 | builder | Self-review bugfix: (1) removed unused numpy import, (2) fixed cross-asset lookback computation — was using raw Series ref_df['close'] mixed into ref_returns.with_columns() which would silently misalign if rows were ever filtered; refactored to compute all return columns on ref_df first using proper pl.col() expressions then select for join. 55/55 tests pass. |
| p1_builder_implement | 2026-03-26 | unknown | auto_wiggum: hard timeout reached, marking complete |
| p1_builder_bugfix | 2026-03-26 | builder | Bugfix already applied in prior session: (1) removed dead numpy import, (2) fixed cross-asset lookback using raw Series — refactored to pl.col() expressions on source df. 55/55 tests pass. Re-completing after hard timeout. |
| p1_critic_review | 2026-03-26 | critic | APPROVED: 0 BLOCKs, 0 HIGH FLAGs, 1 MED FLAG, 2 LOW FLAGs. 55/55 tests GREEN (independently verified). Both bugfix claims confirmed: (1) numpy import removed, (2) cross-asset lookback refactored to pl.col() expressions. 15 independent verifications passed. 61 base features, 73 with cross-asset. All operations causal (28 shifts positive, no center=True). FLAG-1 MED: cumulative VWAP becomes stale on long trending series — consider session-based VWAP in future. FLAG-2 LOW: Ichimoku senkou unshifted (correct for ML). FLAG-3 LOW: _token_return temp column relies on general cleanup. Review at: pipeline_builds/microcap-swing-s2-feature-engineering_critic_review.md |
| p1_complete | 2026-03-26 | critic | Critic approved Phase 1 — clean pass |

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
- **Spec:** `snn_applied_finance/specs/microcap-swing-s2-feature-engineering_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s2-feature-engineering_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s2-feature-engineering_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s2-feature-engineering_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_microcap-swing-s2-feature-engineering.ipynb`
