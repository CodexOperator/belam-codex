---
primitive: pipeline
status: phase1_build
priority: high
version: validate-scheme-b
spec_file: machinelearning/snn_applied_finance/specs/validate-scheme-b_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_validate-scheme-b.ipynb
agents: [architect, critic, builder]
tags: [validation, statistics, snn]
project: snn-applied-finance
started: 2026-03-17
---

# Implementation Pipeline: VALIDATE-SCHEME-B

## Description
Statistical validation of V3 Scheme B (+0.45 Sharpe) with 7+ walk-forward folds to establish significance

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_validate-scheme-b.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-17 | belam-main | Pipeline instance created |
| pipeline_created | 2026-03-17 | belam-main | Pipeline kickoff |
| architect_design | 2026-03-18 | architect | In progress |
| pipeline_created | 2026-03-18 | belam-main | Pipeline kickoff |
| architect_design | 2026-03-18 | architect | Design v1: 12 experiments (3 primary + 4 control + 3 epoch-sensitivity + 2 baseline). Frozen V3 Scheme B, 10 folds, extended data 2020-2025, DSR+bootstrap+t-test. |
| critic_design_review | 2026-03-18 | critic | APPROVED: 0 blocks, 7 flags. FLAG-1: t-test fold non-independence (supplement with sign test + block bootstrap). FLAG-2: target variable undefined. FLAG-3: cost application unspecified. FLAG-4: random seeds missing. FLAG-5: no power analysis. FLAG-6: no paired comparison to controls. FLAG-7: fold boundaries too loose. Checklist 12/14. Strongest statistical design — the verdict (validated/weak/rejected) will be definitive. |
| critic_design_review | 2026-03-18 | critic | APPROVED: 0 blocks, 7 flags |
| critic_design_review | 2026-03-18 | critic | APPROVED: 0 blocks, 7 flags |
| builder_implementation | 2026-03-18 | builder | In progress |
| builder_implementation | 2026-03-18 | builder | crypto_validate-scheme-b_predictor.ipynb: 51 cells, 12 experiments, all 7 FLAGS addressed. Frozen V3 Scheme B architecture, 10 walk-forward folds, DSR+bootstrap+t-test+sign test+block bootstrap+Wilcoxon. Epoch sensitivity experiments (10/25/50/100). |
| architect_design | 2026-03-18 | architect | Design v1: 8 experiments × 13 folds = 104 runs. Core replication of V3 Scheme B (FROZEN config) across 13 walk-forward folds (2020-2026, 4-month val windows). Statistical battery: Sharpe t-test, Deflated Sharpe Ratio (n_trials=54), Bootstrap 95% CI, PBO. 4 diagnostic models (Scheme 0, LSTM, LR, majority) for component attribution. 3 sensitivity runs (HuberLoss delta, abstention threshold). Clear pass/fail criteria: all 3 primary tests must pass for 'validated'. |
| critic_design_review | 2026-03-18 | critic | APPROVED v2 design with 5 FLAGS (no blocks). FLAG-1: DSR variance needs Lo (2002) non-normal adjustment for BTC fat tails. FLAG-2: Bootstrap annualization uses sqrt(252*6) — should be sqrt(365*6) for crypto. FLAG-3: PBO requires all 54 V3 trial results or should be dropped (DSR covers selection bias). FLAG-4: LSTM baseline training protocol unspecified. FLAG-5: Random seeds missing. Checklist 10/14 pass. Strongest statistical design to date. |

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
- **Spec:** `snn_applied_finance/specs/validate-scheme-b_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/validate-scheme-b_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/validate-scheme-b_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/validate-scheme-b_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_validate-scheme-b.ipynb`
