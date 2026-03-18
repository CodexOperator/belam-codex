---
primitive: pipeline
status: phase1_complete
priority: high
version: stack-specialists
spec_file: machinelearning/snn_applied_finance/specs/stack-specialists_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_stack-specialists.ipynb
agents: [architect, critic, builder]
tags: [snn, ensemble, specialists]
project: snn-applied-finance
started: 2026-03-17
---

# Implementation Pipeline: STACK-SPECIALISTS

## Description
Combine CrashDetector + RallyDetector + VolSpikeDetector via logistic regression

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_stack-specialists.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-17 | belam-main | Pipeline instance created |
| pipeline_created | 2026-03-17 | belam-main | Pipeline kickoff |
| pipeline_created | 2026-03-18 | belam-main | Pipeline kickoff |
| architect_design | 2026-03-18 | architect | In progress |
| architect_design | 2026-03-18 | architect | Design v1: 12 experiments (6 stacker + 3 diagnostic + 3 baseline). Frozen V3 specialists, LR stacker on 8 features, Fold 3 held out, anti-leakage design. |
| critic_design_review | 2026-03-18 | critic | APPROVED: 0 blocks, 6 flags. FLAG-1: single evaluation fold — frame as proof-of-concept not statistical evidence. FLAG-2: agreement_score incomplete (recommend dropping it). FLAG-3: abstention threshold doesn't transfer from regression to classification. FLAG-4: random seeds missing. FLAG-5: skewed specialist probabilities. FLAG-6: target variable undefined. Checklist 10/14. Clean anti-leakage design. Watch specialist correlation — if r>0.5, stacking premise collapses. |
| architect_design | 2026-03-18 | architect | Design v1: 12 experiments (6 stacker + 3 diagnostic + 3 baseline). Ensemble of 3 V3 specialists (CrashDet, RallyDet, VolSpikeDet) combined via LogReg/RF/Voting. 8-feature stacker input (3 probs + 3 entropies + max_confidence + agreement_score). Fold 3 held out exclusively for stacker evaluation (no leakage). Key diagnostic ST-DIAG-03 (shuffled labels) validates stacking learns real signal. |
| builder_implementation | 2026-03-18 | builder | In progress |
| builder_implementation | 2026-03-18 | builder | crypto_stack-specialists_predictor.ipynb: 46 cells, 12 experiments (6 stacker + 3 diagnostic + 3 baseline). All 6 FLAGS addressed. Anti-leakage design with sacred Fold 3 hold-out. Specialists retrained from V3 spec. |
| critic_code_review | 2026-03-18 | critic | APPROVED: 0 blocks, 4 flags. FLAG-1: hash() non-deterministic seeds (use hashlib.md5). FLAG-2: IID bootstrap on autocorrelated PnL. FLAG-3: BL-02 hardcoded approximation. FLAG-4: abstention edge case. Missing: calibration diagram. All 6 design flags addressed. 20/24 checklist. Anti-leakage correct. Notebook ready to run. |
| critic_code_review | 2026-03-18 | critic | APPROVED: 0 blocks, 4 flags. All 6 design flags addressed. 20/24 checklist. Notebook ready to run. |
| phase1_complete | 2026-03-18 | architect | Phase 1 complete. Critic code review APPROVED (20/24 checklist, 0 blocks, 4 non-blocking flags). 46-cell notebook: 3 frozen V3 specialists (CrashDet, RallyDet, VolSpikeDet) stacked via LR/RF/Voting on 6 features (3 probs + 3 entropies). Anti-leakage correct (OOF predictions, sacred Fold 3 hold-out). All 6 design flags addressed. Remaining flags: hash() seeds (recurring pattern — use hashlib), IID bootstrap on autocorrelated PnL, hardcoded V3 reference, abstention edge case. Notebook ready for Shael review. |
| critic_code_review | 2026-03-18 | critic | APPROVED: 0 blocks, 4 flags. All 6 design flags addressed. 20/24 checklist. Notebook ready to run. |

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
- **Spec:** `snn_applied_finance/specs/stack-specialists_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/stack-specialists_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/stack-specialists_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/stack-specialists_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_stack-specialists.ipynb`
