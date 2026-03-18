---
primitive: pipeline
status: phase1_complete
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
| builder_implementation | 2026-03-18 | builder | crypto_validate-scheme-b_predictor.ipynb: 51 cells (25 code, 26 markdown), 12 experiments, all 7 FLAGS addressed. Frozen V3 Scheme B architecture, 10 walk-forward folds, DSR+bootstrap+t-test+sign test+block bootstrap+Wilcoxon. Epoch sensitivity (10/25/50/100). Build script: build_validate_scheme_b.py. RECOVERY: notebook was built in prior session but orchestrator handoff was missed due to timeout. |
| builder_implementation | 2026-03-18 | builder | RECOVERY: 51-cell notebook complete, all 7 FLAGS addressed |
| builder_implementation | 2026-03-18 | builder | RECOVERY: 51-cell notebook complete, all 7 FLAGS addressed. Frozen V3 Scheme B, 10 folds, DSR+bootstrap+t-test+sign test+block bootstrap+Wilcoxon. |
| critic_code_review_blocked | 2026-03-18 | critic | BLOCKED: BLOCK-1: BL-01/BL-02 baselines crash with KeyError: data_dict['labels'] — data_bundle has keys 'delta'/'pop', not 'labels'. Fix: data_dict['delta']['labels'] in majority/random branches (3 lines). 5 FLAGS: DSR skewness/kurtosis defaults to normal (BTC fat tails), hash() non-deterministic seeds, binom_test deprecated, PBO dropped without documentation note, missing design sections. All 7 original design flags verified as implemented. Checklist 21/23. Statistical battery is excellent — best validation pipeline we've built. |
| critic_code_review_blocked | 2026-03-18 | critic | BLOCKED: BLOCK-1: BL-01/BL-02 baselines crash with KeyError — data_dict['labels'] accessed on bundle dict {'delta':..,'pop':..} which has no 'labels' key. Fix: data_dict['delta']['labels']. Also 5 FLAGS: (1) DSR Lo adjustment called with normality defaults, (2) hash() non-deterministic seeds, (3) n_folds=10 vs design 13, (4) n_trials_dsr=10 vs 54, (5) baseline results missing net_sharpe_abst key. |
| builder_apply_blocks | 2026-03-18 | builder | In progress |
| critic_code_review_blocked | 2026-03-18 | critic | BLOCKED: BLOCK-1: BL-01/BL-02 KeyError crash. 5 FLAGS. See validate-scheme-b_critic_code_review.md |
| critic_code_review_blocked | 2026-03-18 | critic | BLOCKED: BLOCK-1: BL-01/BL-02 KeyError crash. 5 FLAGS. 21/23 checklist. Fix 3 lines in Cell 27. |
| builder_apply_blocks | 2026-03-18 | builder | Fixed BLOCK-1 (BL-01/BL-02 KeyError: data_dict['delta']['labels']) + all 5 FLAGS: (1) DSR Lo non-normal adjustment with actual BTC skew/kurtosis, (2) hashlib.md5 deterministic seeds, (3) n_folds=10 documented, (4) n_trials_dsr=10 documented, (5) net_sharpe_abst added to all baseline results. Also S-1: binomtest replaces deprecated binom_test. Committed 799c7e2. |
| critic_code_review | 2026-03-18 | critic | APPROVED: All 7 fixes verified (BLOCK-1 KeyError, FLAG-1 DSR Lo non-normal, FLAG-2 hashlib seeds, FLAG-3 n_folds doc, FLAG-4 n_trials doc, FLAG-5 net_sharpe_abst, S-1 binomtest). 9/9 checklist pass. No regressions. Notebook ready to run. |
| critic_code_review | 2026-03-18 | critic | APPROVED: All 7 fixes verified. 9/9 checklist. Notebook ready to run. |
| critic_code_review | 2026-03-18 | critic | APPROVED: All fixes verified. Ready to run. |
| critic_code_review | 2026-03-18 | critic | APPROVED: All 7 fixes verified (BLOCK-1 KeyError, FLAGS 1-5, S-1 binomtest). 9/9 checklist. Notebook ready to run. |
| phase1_complete | 2026-03-18 | architect | Phase 1 complete. Critic code review v2 APPROVED (9/9 checklist, all fixes verified). 51-cell notebook: frozen V3 Scheme B across 10 walk-forward folds, statistical battery includes t-test + sign test + DSR (Lo non-normal adjustment) + bootstrap CI + block bootstrap + Wilcoxon + power analysis. All 7 original issues resolved (BLOCK-1 KeyError, FLAG-1 DSR skew/kurtosis, FLAG-2 hashlib seeds, FLAG-3 n_folds doc, FLAG-4 n_trials doc, FLAG-5 net_sharpe_abst, S-1 binomtest). Notebook ready for Shael review. |

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
