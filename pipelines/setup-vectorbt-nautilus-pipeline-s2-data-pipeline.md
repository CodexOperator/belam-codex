---
primitive: pipeline
status: archived
priority: high
type: builder-first
version: setup-vectorbt-nautilus-pipeline-s2-data-pipeline
spec_file: machinelearning/snn_applied_finance/specs/setup-vectorbt-nautilus-pipeline-s2-data-pipeline_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_setup-vectorbt-nautilus-pipeline-s2-data-pipeline.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [snn, finance]
project: snn-applied-finance
started: 2026-03-25
---

# Implementation Pipeline: SETUP-VECTORBT-NAUTILUS-PIPELINE-S2-DATA-PIPELINE

## Description
Data pipeline for BTC/USDT backtesting

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_setup-vectorbt-nautilus-pipeline-s2-data-pipeline.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-25 | belam-main | Pipeline instance created |
| p1_builder_implement | 2026-03-25 | builder | Implemented 4 modules: D1: binance_fetcher.py (Binance public API, pagination, rate-limit, 1000-candle pages). D2: duckdb_store.py (OHLCV table with PK, upsert/query/info). D3: preprocessor.py (returns, realized+Parkinson vol, volume MA ratio, VWAP dev, RSI/BB/ATR, fracdiff d=0.4 threshold=1e-3). D4: pipeline.py (fetch→store→preprocess orchestration, incremental updates). D5: test_data_pipeline.py — 27 tests (5 fetcher, 8 store, 10 preprocessor, 4 end-to-end). All 27/27 pytest GREEN. |
| p1_builder_bugfix | 2026-03-25 | builder | Bugfix audit complete: no bugs found. All 5 deliverable files present and syntactically clean. No bare excepts, no TODOs/FIXMEs. All imports resolve correctly. 49/49 pytest GREEN (S1: 22 + S2: 27). No stale imports or dead code. |
| p1_critic_review | 2026-03-25 | critic | APPROVED: 0 BLOCKs, 0 HIGH FLAGs, 2 MED FLAGs, 1 LOW FLAG. 27/27 tests GREEN (verified independently). All 5 deliverables clean. Correct causal feature engineering (no lookahead), Parkinson vol formula verified, fracdiff threshold=1e-3 per S1 lesson, DuckDB upsert transactional+idempotent, SQL injection mitigated by DuckDB binder. FLAG-1 MED: query() columns uses f-string (safe but not parameterized). FLAG-2 MED: 9 tests hit live Binance API (flaky offline). FLAG-3 LOW: incremental on empty store silently fetches last 1000 candles. GARCH mentioned in docstring but not implemented (suggestion only). Review at: pipeline_builds/setup-vectorbt-nautilus-pipeline-s2-data-pipeline_critic_review.md |

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
- **Spec:** `snn_applied_finance/specs/setup-vectorbt-nautilus-pipeline-s2-data-pipeline_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/setup-vectorbt-nautilus-pipeline-s2-data-pipeline_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/setup-vectorbt-nautilus-pipeline-s2-data-pipeline_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/setup-vectorbt-nautilus-pipeline-s2-data-pipeline_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_setup-vectorbt-nautilus-pipeline-s2-data-pipeline.ipynb`
