---
primitive: pipeline
status: archived
priority: high
type: builder-first
version: setup-vectorbt-nautilus-pipeline-s5-transaction-costs
spec_file: machinelearning/snn_applied_finance/specs/setup-vectorbt-nautilus-pipeline-s5-transaction-costs_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_setup-vectorbt-nautilus-pipeline-s5-transaction-costs.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [snn, finance]
project: snn-applied-finance
started: 2026-03-25
---

# Implementation Pipeline: SETUP-VECTORBT-NAUTILUS-PIPELINE-S5-TRANSACTION-COSTS

## Description
Transaction cost analysis and optimization

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_setup-vectorbt-nautilus-pipeline-s5-transaction-costs.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-25 | belam-main | Pipeline instance created |
| p1_builder_implement | 2026-03-25 | builder | 5 deliverables: D1: costs/models.py (ExchangeFeeSchedule with Binance spot/futures VIP0-9, SlippageModel, MarketImpactModel sqrt Almgren-Chriss, SpreadCostModel, FundingRateModel perp futures, CostStack composable chain with to_vectorbt_params). D2: costs/analysis.py (CostAttribution with per-trade breakdown and trades_killed_by_costs, BreakEvenAnalyzer with break_even_return and cost_adjusted_sharpe, CostSensitivitySweep with fee/slippage/frequency sensitivity). D3: costs/__init__.py (public exports). D4: tests/test_transaction_costs.py — 50 tests (6 fee schedule, 3 slippage, 5 market impact, 3 spread, 5 funding, 7 cost stack, 3 factory, 5 attribution, 5 break-even, 5 sensitivity, 3 integration). 195/195 pytest GREEN across S1-S5. |
| p1_builder_bugfix | 2026-03-25 | builder | Bugfix audit: 1 dead import found and removed (field from dataclasses in analysis.py — imported but never used). No logic bugs found. 6 verification audits passed: (1) FundingRateModel directional symmetry (long pays, short earns, symmetric). (2) CostStack round-trip with funding correctly cancels. (3) MarketImpactModel handles negative ADV. (4) CostAttribution net_returns correctly deducts round-trip costs (verified: 5% gross - 2% RT cost = 3% net). (5) All 5 components implement CostComponent protocol. (6) BreakEvenAnalyzer math verified (16 bps one-way → 32 bps RT → 0.32% break-even). No bare excepts, no TODO/FIXME. 195/195 pytest GREEN across S1-S5. |
| p1_critic_review | 2026-03-25 | critic | APPROVED: 0 BLOCKs, 1 MED FLAG, 2 LOW FLAGs. 50/50 tests GREEN (verified independently). 11 independent verifications passed. FLAG-1 MED: CostAttribution.net_returns() doubles one-side cost for round-trip instead of summing buy+sell — incorrect with FundingRateModel (4x overestimate for buy trades with perp funding). Does not affect spot backtesting (symmetric costs). CostStack.round_trip_bps() IS correct. FLAG-2 LOW: 5 unused imports in analysis.py (ExchangeFeeSchedule, FundingRateModel, MarketImpactModel, SlippageModel, SpreadCostModel imported but only CostStack used). FLAG-3 LOW: full_sensitivity_report() leaves net_sharpe_at_default_cost as None (never filled). Architecture is solid: Protocol-based CostComponent, frozen dataclasses, additive CostStack, correct VBT bridge excluding funding. Realistic Binance VIP0-9 tiers, Almgren-Chriss sqrt impact. Review at: pipeline_builds/setup-vectorbt-nautilus-pipeline-s5-transaction-costs_critic_review.md |

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
- **Spec:** `snn_applied_finance/specs/setup-vectorbt-nautilus-pipeline-s5-transaction-costs_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/setup-vectorbt-nautilus-pipeline-s5-transaction-costs_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/setup-vectorbt-nautilus-pipeline-s5-transaction-costs_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/setup-vectorbt-nautilus-pipeline-s5-transaction-costs_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_setup-vectorbt-nautilus-pipeline-s5-transaction-costs.ipynb`
