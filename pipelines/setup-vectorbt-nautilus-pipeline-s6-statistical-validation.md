---
primitive: pipeline
status: archived
priority: high
type: builder-first
version: setup-vectorbt-nautilus-pipeline-s6-statistical-validation
spec_file: machinelearning/snn_applied_finance/specs/setup-vectorbt-nautilus-pipeline-s6-statistical-validation_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_setup-vectorbt-nautilus-pipeline-s6-statistical-validation.ipynb
agents: [architect, critic, builder]
supersedes: 
tags: [snn, finance]
project: snn-applied-finance
started: 2026-03-25
pending_action: p1_complete
current_phase: 
dispatch_claimed: false
last_updated: 2026-03-25 13:39
reset: false
---
# Implementation Pipeline: SETUP-VECTORBT-NAUTILUS-PIPELINE-S6-STATISTICAL-VALIDATION

## Description
Statistical validation and robustness testing

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_setup-vectorbt-nautilus-pipeline-s6-statistical-validation.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-25 | belam-main | Pipeline instance created |
| p1_builder_implement | 2026-03-25 | unknown |  |
| p1_builder_bugfix | 2026-03-25 | builder | Bugfix audit found 2 dead imports (math, dataclass) removed and 1 bug fixed: Durbin-Watson division-by-zero on constant returns — added ss_resid < 1e-15 guard with early return. Verified: BH/Holm/Bonferroni tie-handling correct, CSCV uneven groups no data loss, White's RC centering correct, bootstrap CI logic correct, permutation sidedness correct. No bare excepts, no TODO/FIXME. 249/249 pytest GREEN across S1-S6. |
| p1_critic_review | 2026-03-25 | ubuntu | In progress |
| p1_builder_bugfix | 2026-03-25 | unknown |  |
| p1_critic_review | 2026-03-25 | critic | APPROVED: 0 BLOCKs, 1 MED FLAG, 2 LOW FLAGs. 54/54 tests GREEN (verified independently). All 8 statistical test categories verified: multiple testing (BH/Holm/Bonferroni), bootstrap CIs, permutation tests, White's RC, CSCV, stationarity (ADF+KPSS), serial dependence (Ljung-Box+DW), distribution (JB+AD). Bugfix claims verified: DW division-by-zero guard works, dead imports removed, CSCV uneven groups no data loss, White's RC centering correct, permutation sidedness correct. FLAG-1 MED: scipy.stats.anderson FutureWarning — will break on SciPy 1.19+ (critical_values/significance_level attrs deprecated). FLAG-2 LOW: fp noise in permutation IID p-values (0.956 not 1.0). FLAG-3 LOW: no cross-module integration test between statistical.py and analysis.py. DSR consistency with S4 fix confirmed (monotonically decreasing with trials). 249/249 S1-S6 cumulative tests GREEN. Review at: pipeline_builds/setup-vectorbt-nautilus-pipeline-s6-statistical-validation_critic_review.md |

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
- **Spec:** `snn_applied_finance/specs/setup-vectorbt-nautilus-pipeline-s6-statistical-validation_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/setup-vectorbt-nautilus-pipeline-s6-statistical-validation_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/setup-vectorbt-nautilus-pipeline-s6-statistical-validation_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/setup-vectorbt-nautilus-pipeline-s6-statistical-validation_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_setup-vectorbt-nautilus-pipeline-s6-statistical-validation.ipynb`
