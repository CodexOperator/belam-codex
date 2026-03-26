---
primitive: pipeline
status: archived
archive_date: 2026-03-26T01:16Z
archive_reason: "Phase 1 complete, critic approved"
priority: critical
type: builder-first
version: microcap-swing-s1-data-pipeline-v4
spec_file: machinelearning/snn_applied_finance/specs/microcap-swing-s1-data-pipeline-v4_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_microcap-swing-s1-data-pipeline-v4.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [quant, crypto, microcap, data-pipeline]
project: microcap-swing-signal-extraction
started: 2026-03-26
---

# Implementation Pipeline: MICROCAP-SWING-S1-DATA-PIPELINE-V4

## Description
S1: Data Pipeline — CEX (ccxt) + DEX (Birdeye/Jupiter) + Fear & Greed API. Local Python scripts in machinelearning/microcap_swing/src/data_pipeline.py. See tasks/microcap-swing-signal-extraction.md S1 for full spec and acceptance criteria. Use Polars for data processing, Parquet for storage, pytest for tests.

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_microcap-swing-s1-data-pipeline-v4.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-26 | belam-main | Pipeline instance created |
| p1_builder_implement | 2026-03-26 | builder | S1 Data Pipeline implemented: src/data_pipeline.py with CEX (ccxt/Binance), DEX (Birdeye/DexScreener), Fear & Greed collectors. Quality checks (gap detection, volume anomalies, price spikes, zero-vol streaks). Resampling to 15m/1h. Polars + Parquet throughout. configs/tokens.yaml with all token tiers. 25/25 pytest tests passing. CLI with --tokens, --all, --days, --force, --fear-greed-only, --quality-report flags. |
| p1_builder_bugfix | 2026-03-26 | builder | Bugfix pass: (1) Added MAX_RETRIES=5 to CEX retry loops preventing infinite hangs on persistent network errors. (2) Removed unused imports (json, sys). (3) Fixed quality_report_only mode to load existing parquet data instead of collecting. (4) Replaced slow map_elements lambda in F&G regime duration with native pl.lit(1).cum_sum().over(). (5) Added schema validation on incremental merge to prevent concat crashes. (6) Added __main__.py for proper module invocation. 25/25 tests still passing. |
| p1_builder_implement | 2026-03-26 | unknown | auto_wiggum: hard timeout reached, marking complete |
| p1_builder_bugfix | 2026-03-26 | builder | Duplicate dispatch — bugfix already completed in prior turn. All 6 fixes applied: MAX_RETRIES on CEX loops, unused imports removed, quality_report_only mode fixed, map_elements replaced with native Polars, schema validation on incremental merge, __main__.py added. 25/25 tests passing. Critic already dispatched at 00:56. |
| p1_critic_review | 2026-03-26 | critic | CODE APPROVED: Clean S1 data pipeline. 25/25 tests green. No blockers. 4 low-priority flags (no retry on DEX/F&G, empty DexScreener pair_addresses, F&G quality gap). See critic_code_review.md for full review. |
| p1_critic_review | 2026-03-26 | unknown | auto_wiggum: hard timeout reached, marking complete |

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
- **Spec:** `snn_applied_finance/specs/microcap-swing-s1-data-pipeline-v4_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s1-data-pipeline-v4_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s1-data-pipeline-v4_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/microcap-swing-s1-data-pipeline-v4_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_microcap-swing-s1-data-pipeline-v4.ipynb`
