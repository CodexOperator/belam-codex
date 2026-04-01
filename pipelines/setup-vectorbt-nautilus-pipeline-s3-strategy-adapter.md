---
primitive: pipeline
status: archived
priority: high
type: builder-first
version: setup-vectorbt-nautilus-pipeline-s3-strategy-adapter
spec_file: machinelearning/snn_applied_finance/specs/setup-vectorbt-nautilus-pipeline-s3-strategy-adapter_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_setup-vectorbt-nautilus-pipeline-s3-strategy-adapter.ipynb
agents: [architect, critic, builder]
supersedes: 
tags: [snn, finance]
project: snn-applied-finance
started: 2026-03-25
pending_action: p1_complete
current_phase: 
dispatch_claimed: false
last_updated: 2026-03-25 05:27
reset: false
---
# Implementation Pipeline: SETUP-VECTORBT-NAUTILUS-PIPELINE-S3-STRATEGY-ADAPTER

## Description
Strategy adapter for SNN model integration

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_setup-vectorbt-nautilus-pipeline-s3-strategy-adapter.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-25 | belam-main | Pipeline instance created |
| p1_builder_implement | 2026-03-25 | builder | S3 strategy adapter implemented: 5 deliverables, 46/46 tests GREEN |
| p1_builder_implement | 2026-03-25 | builder | 5 deliverables: base_adapter.py, vectorbt_adapter.py, nautilus_adapter.py, __init__.py, test_strategy_adapter.py. 46/46 tests pass. |
| p1_builder_bugfix | 2026-03-25 | builder | Bugfix audit found and fixed 1 bug + 2 doc issues: (1) BUG FIX: confidence sizing was dead code — _compute_sizes() was called but size=np.inf overrode it, making size_mode=confidence identical to fixed. Fixed by using size_type=value with cash-denominated sizes for confidence mode, and size_type=amount with np.inf for fixed mode. Added regression test proving confidence != fixed returns. (2) DOC FIX: Removed nonexistent kelly sizing mode from docstring. (3) DOC FIX: Corrected nautilus_adapter usage example (config takes strings, not InstrumentId/BarType/Decimal objects). 46/46 tests GREEN. |
| p1_critic_review | 2026-03-25 | critic | APPROVED: 0 BLOCKs, 0 HIGH FLAGs, 1 MED FLAG, 1 LOW FLAG. 46/46 tests GREEN (verified independently). All 3 bugfix claims verified: (1) confidence sizing was dead code — fixed with size_type=value + cash-denominated sizes, regression test proves fixed!=confidence returns (0.118 vs 0.043). (2) Kelly removed from docstrings — grep confirmed zero references. (3) Nautilus config uses strings — SNNStrategyConfig fields are str, conversion in __init__. FLAG-1 MED: confidence sizing uses init_cash not current portfolio value — documented approximation, acceptable for research. FLAG-2 LOW: lazy import in _generate_current_signal. 5 deliverables, 1644L total, clean architecture. Review at: pipeline_builds/setup-vectorbt-nautilus-pipeline-s3-strategy-adapter_critic_review.md |

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
- **Spec:** `snn_applied_finance/specs/setup-vectorbt-nautilus-pipeline-s3-strategy-adapter_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/setup-vectorbt-nautilus-pipeline-s3-strategy-adapter_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/setup-vectorbt-nautilus-pipeline-s3-strategy-adapter_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/setup-vectorbt-nautilus-pipeline-s3-strategy-adapter_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_setup-vectorbt-nautilus-pipeline-s3-strategy-adapter.ipynb`
