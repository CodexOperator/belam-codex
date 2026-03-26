---
primitive: pipeline
status: p2_complete
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

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| p2_architect_design | 2026-03-26 | architect | Phase 2 design: 4 deliverables (~123 lines, 7 tests). (1) Session-windowed VWAP addressing FLAG-1 MED — rolling 96-candle VWAP to complement cumulative. (2) Cross-asset temp column cleanup for FLAG-3 LOW. (3) Feature manifest JSON for S3A/S3B downstream readiness. (4) Graceful stubs for unavailable spec features (onchain, market structure) with stable function signatures. Design at: pipeline_builds/microcap-swing-s2-feature-engineering_phase2_architect_design.md |
| p2_builder_implement | 2026-03-26 | builder | Phase 2 implemented: all 4 deliverables. D1: compute_session_vwap() — rolling windowed VWAP (96 candles = 24h default) with price_session_vwap_dist, added to FeatureConfig.session_vwap_windows, wired into compute_all_features. D2: _token_return cleanup in compute_cross_asset_features() — one-liner drop guard, no more temp column leakage on standalone use. D3: generate_feature_manifest() + save_feature_manifest() — machine-readable JSON with per-feature dtype/category/null_rate/stats, category_counts summary, auto-generated on --feature-report. D4: compute_onchain_features() + compute_market_structure_features() stubs — check for optional data dirs, load parquet + as-of join if present, return df unchanged if absent. No dummy columns. Both wired into compute_all_features. 7 new tests (2 session VWAP, 1 cross-asset cleanup, 2 manifest, 2 stubs). 37/37 S2 tests GREEN, 112/112 total tests GREEN. |
| p2_builder_bugfix | 2026-03-26 | builder | Bugfix audit: no bugs found. Verified: (1) all imports used (json added for manifest, no dead imports), (2) no TODO/FIXME/HACK markers, (3) session VWAP rolling_sum produces correct null pattern (null for first w-1 rows, valid after), (4) _token_return cleanup guard works correctly — column dropped when present, no-op when absent, (5) feature manifest generates valid JSON with all required keys, (6) onchain/market structure stubs return df unchanged with correct column set when data dirs absent, (7) no temp columns leak from any new function. 112/112 tests GREEN. |
| p2_critic_review | 2026-03-26 | critic | APPROVED: 0 BLOCKs, 0 FLAGs. All 4 Phase 2 deliverables verified: (1) Session VWAP rolling_sum produces correct null pattern and responsive distance metric, (2) _token_return cleanup guard works both ways, (3) Feature manifest generates valid JSON with all required keys and zero null rates, (4) Onchain/market structure stubs return df unchanged with no dummy columns. 37/37 S2 tests GREEN, 112/112 total tests GREEN (independently verified). All Phase 1 FLAGs resolved. Review at: pipeline_builds/microcap-swing-s2-feature-engineering_phase2_critic_review.md |

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
