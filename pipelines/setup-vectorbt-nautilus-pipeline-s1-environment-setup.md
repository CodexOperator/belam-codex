---
primitive: pipeline
status: p1_complete
priority: high
type: builder-first
version: setup-vectorbt-nautilus-pipeline-s1-environment-setup
spec_file: machinelearning/snn_applied_finance/specs/setup-vectorbt-nautilus-pipeline-s1-environment-setup_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_setup-vectorbt-nautilus-pipeline-s1-environment-setup.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [snn, finance]
project: snn-applied-finance
started: 2026-03-25
---

# Implementation Pipeline: SETUP-VECTORBT-NAUTILUS-PIPELINE-S1-ENVIRONMENT-SETUP

## Description
Install VectorBT PRO, NautilusTrader, supporting libs. Pin versions. Smoke test imports and trivial backtest.

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_setup-vectorbt-nautilus-pipeline-s1-environment-setup.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-25 | belam-main | Pipeline instance created |
| p1_builder_implement | 2026-03-25 | builder | Re-implemented all 4 deliverables. D1: requirements-backtest.txt (vectorbt 0.28.4, nautilus_trader 1.224.0, polars 1.39.3, duckdb 1.5.1, arch 8.0.0, skfolio 0.16.1). D2: backtesting/ directory structure with 5 subdirs + __init__.py files. D3: tests/test_backtest_env.py — 22 tests (imports, VectorBT MA crossover backtest, NautilusTrader engine, dir structure, fracdiff shim). D4: scripts/setup_backtest_env.sh. 22/22 pytest GREEN. |
| p1_builder_bugfix | 2026-03-25 | builder | Bugfix audit: no bugs found. All 5 deliverable files present. No stale imports. 22/22 pytest GREEN. VectorBT freq warnings are cosmetic (need freq param for annualized ratios). |
| p1_critic_review | 2026-03-25 | critic | APPROVED: 0 BLOCKs, 0 HIGH FLAGs, 1 MED FLAG. 22/22 tests GREEN (verified independently). All 6 packages match pinned versions. D1-D5 all present and correct. FLAG-1 MED: fracdiff_shim default threshold=1e-5 produces 927 weights for d=0.5 — output is 1 point from a 252-day series. Callers must override (threshold=1e-2 gives 243 output). Algorithm correct, default impractical. VectorBT freq warnings cosmetic. Review at: pipeline_builds/setup-vectorbt-nautilus-pipeline-s1-environment-setup_critic_review.md |

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
- **Spec:** `snn_applied_finance/specs/setup-vectorbt-nautilus-pipeline-s1-environment-setup_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/setup-vectorbt-nautilus-pipeline-s1-environment-setup_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/setup-vectorbt-nautilus-pipeline-s1-environment-setup_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/setup-vectorbt-nautilus-pipeline-s1-environment-setup_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_setup-vectorbt-nautilus-pipeline-s1-environment-setup.ipynb`
