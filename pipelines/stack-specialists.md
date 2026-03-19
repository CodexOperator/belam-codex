---
primitive: pipeline
status: experiment_running
priority: high
version: stack-specialists
spec_file: machinelearning/snn_applied_finance/specs/stack-specialists_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/crypto_stack-specialists_predictor.ipynb
agents: [architect, critic, builder]
tags: [snn, ensemble, specialists]
project: snn-applied-finance
started: 2026-03-17
---

# Implementation Pipeline: STACK-SPECIALISTS

## Description
Combine CrashDetector + RallyDetector + VolSpikeDetector via logistic regression

## Notebook Convention
**All phases live in a single notebook** (`crypto_stack-specialists_predictor.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

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
| phase1_revision_architect | 2026-03-19 | coordinator | In progress |
| phase1_revision_architect | 2026-03-19 | architect | Revised design v2: 4 changes from coordinator direction. R1: membrane readout verification gate. R2/R3: 4-test specialist aliveness battery (pred variance, minority-class detection, loss vs constant, unique outputs) — dead specialists excluded, abort if zero alive. R4: 3 scale experiments (0.5/1.0/2.0) per ANCOVA finding (scale matters more than encoding). Added gate criteria before stacking claims. 15 total experiments (up from 12). Calibration diagram now explicit in structure. All 4 critic code review FLAGs carried forward. |
| phase1_revision_critic_review | 2026-03-19 | critic | APPROVED with 5 FLAGS (0 blocks). All 4 coordinator direction points addressed. FLAG-1: Aliveness Test 3 (loss vs constant) may be too strict for minority-event specialists — recommend AUC>0.52 instead. FLAG-2: Scale selection on Fold 3 is data snooping — select based on specialist prediction quality, not sacred hold-out. FLAG-3: Conservative all-folds-alive may over-exclude (sensitivity analysis). FLAG-4: Correlation threshold relaxed to 0.7 without graded interpretation. FLAG-5: hashlib.md5 seeds now mandatory (3rd time flagged). Checklist 12/14. Review at: pipeline_builds/stack-specialists_critic_revision_review.md |
| phase1_revision_critic_review | 2026-03-19 | critic | APPROVED 5 FLAGS 0 blocks. Review at: pipeline_builds/stack-specialists_critic_revision_review.md |
| phase1_revision_builder | 2026-03-19 | builder | Revised notebook v2: 73 cells (34 code, 39 markdown), 15 experiments (3 scale + 6 stacker + 3 diagnostic + 3 baseline). All 4 coordinator direction points implemented: R1 membrane readout verification (3-check gate), R2 zero-learning detection (stacker input variance), R3 aliveness battery (4 tests per specialist per fold per scale), R4 scale sensitivity (0.5/1.0/2.0). All 5 Critic revision FLAGS addressed: FLAG-1 AUC>0.52 for Test 3, FLAG-2 scale selection by specialist quality not Fold 3, FLAG-3 per-fold sensitivity analysis, FLAG-4 graded correlation interpretation, FLAG-5 hashlib.md5 mandatory. Added calibration diagram, gate criteria, block bootstrap. |
| phase1_revision_builder | 2026-03-19 | builder | Revised notebook v2: 73 cells (34 code, 39 markdown), 15 experiments. All 4 coordinator direction points + 5 Critic revision FLAGS addressed. R1 membrane readout verification, R2 zero-learning detection, R3 aliveness battery (AUC>0.52), R4 scale sweep. Gate criteria, calibration diagram, block bootstrap added. |
| phase1_revision_code_review | 2026-03-19 | critic | APPROVED with 2 FLAGS (0 blocks). All 4 coordinator direction points verified: R1 membrane gate, R2 zero-learning detection, R3 aliveness battery (AUC>0.52), R4 scale sensitivity (3 scales). All 5 revision FLAGS addressed: FLAG-1 AUC for Test 3, FLAG-2 scale by quality not Fold 3, FLAG-3 per-fold sensitivity, FLAG-4 graded correlation, FLAG-5 hashlib.md5. All 4 v1 FLAGS resolved. FLAGS: (1) voting_predict mutable default param (minor), (2) BL-02 still hardcoded (carry-forward). 23/24 checklist. Review at: pipeline_builds/stack-specialists_critic_revision_code_review.md |
| phase1_complete | 2026-03-19 | architect | Phase 1 revision COMPLETE. Critic code review v2 APPROVED 23/24 checklist, 0 blocks, 2 non-blocking FLAGS: (1) voting_predict mutable default param (minor, not a bug in current flow), (2) BL-02 still hardcoded (carry-forward, V3 weights unavailable). v2 notebook: 73 cells, 15 experiments (3 scale + 6 stacker + 3 diagnostic + 3 baseline). All 4 coordinator direction points implemented and verified: R1 membrane readout gate, R2 zero-learning detection, R3 specialist aliveness battery (AUC>0.52), R4 scale sensitivity (3 scales). All 5 revision FLAGS + all 4 v1 FLAGS resolved. Major v1→v2 improvements: defensive gates, aliveness battery, scale testing, calibration diagram, block bootstrap, deterministic hashlib seeds. Notebook ready for Shael review. |
| local_experiment_running | 2026-03-19 | system | Local experiment run started (PID: 2568685) |
| local_experiment_running | 2026-03-19 | system | EXPERIMENT FAILED after 1 attempts: Process exited with code 1 |

## Local Experiment Execution
_Status: Auto-triggered on Phase 1 completion_

Experiments run locally on the VPS via `run_experiment.py`. The pipeline auto-transitions:
`phase1_complete` → `experiment_running` → `experiment_complete` → Phase 2

- **Results:** `notebooks/local_results/stack-specialists/`
- **Manual trigger:** `belam run stack-specialists`

### Experiment History
| Run | Date | Duration | Experiments | Errors | Notes |
|-----|------|----------|-------------|--------|-------|

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on experiment completion_

### Feedback
_(Shael's feedback goes here when experiments are complete and reviewed)_

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
- **Notebook:** `snn_applied_finance/notebooks/crypto_stack-specialists_predictor.ipynb`
