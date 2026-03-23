---
primitive: pipeline
status: archived
priority: high
version: stack-specialists
spec_file: machinelearning/snn_applied_finance/specs/stack-specialists_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/crypto_stack-specialists_predictor.ipynb
agents: [architect, critic, builder]
tags: [snn, ensemble, specialists]
project: snn-applied-finance
started: 2026-03-17
archived: 2026-03-20
version_label: v5-stacking
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
| local_experiment_running | 2026-03-19 | system | Experiment run started (PID: 2576537, mode: supervised) |
| local_experiment_running | 2026-03-19 | system | EXPERIMENT FAILED after 5 attempts: Builder failed after 5 attempts |
| local_experiment_running | 2026-03-19 | system | Experiment run started (PID: 2578404, mode: supervised) |
| local_experiment_running | 2026-03-19 | system | EXPERIMENT FAILED after 5 attempts: Builder failed after 5 attempts |
| local_experiment_running | 2026-03-19 | builder | RESULTS: 15 experiments (3 SC + 6 ST + 3 DIAG + 3 BL), 10.3min. ALL GATES PASS. Best: ST-03 (LR C=1.0) 51.93% acc (+1.62pp lift). All Sharpe negative. 3/3 specialists alive at best scale=2.0. Null model close at 50.55%. V3 ref 52.0% still beats best stacker. |
| local_analysis_architect | 2026-03-19 | system | Local analysis started. Results at machinelearning/snn_applied_finance/notebooks/local_results/stack-specialists/ |
| local_analysis_architect | 2026-03-19 | architect | Analysis report complete. VERDICT: Stacking FAILS all primary criteria. Best stacker 51.93% accuracy but -0.84 Sharpe (not profitable). Shuffled-labels null beats 8/12 real experiments. Abstention mechanism completely fails (0% coverage). V3 Scheme B (52%, +0.45 Sharpe) strictly superior. Specialists too correlated (r=0.671) and event→direction mapping too lossy. Scale sensitivity negligible. Recommend deprioritizing stacking in favor of monolithic approaches. 6 additional analysis scripts specified. |
| local_analysis_architect | 2026-03-19 | architect | Analysis report complete. Stacking FAILS all criteria. V3 Scheme B strictly superior. 6 analysis scripts specified. |
| local_analysis_critic_review | 2026-03-19 | critic | APPROVED: 0 blocks, 5 flags. FLAG-1 (HIGH): ST-02 and SC-03 are identical experiments — 14 unique experiments not 15. FLAG-2: shuffled beats 8/12 count imprecise (actual 10/13). FLAG-3: Scripts 1-5 require notebook modification (raw predictions not saved in pkl) — only Script 6 executable from current data. FLAG-4: abstention 12/15 count misleading (all 14 real experiments have zero/negligible coverage). FLAG-5: binomial z minor rounding. Verdict well-supported — stacking convincingly rejected. Key insight: composition at prediction level fails; composition must happen at architectural level. Review at: pipeline_builds/stack-specialists_critic_analysis_review.md |
| local_analysis_critic_review | 2026-03-19 | critic | APPROVED 0 blocks 5 flags |
| local_analysis_critic_review | 2026-03-19 | critic | APPROVED 0 blocks 5 flags. Review at: pipeline_builds/stack-specialists_critic_analysis_review.md |
| local_analysis_builder | 2026-03-19 | builder | Follow-up analysis complete: 6 scripts + 5 FLAG corrections + addendum. All 5 Critic FLAGs addressed: FLAG-1 ST-02=SC-03 confirmed (14 unique experiments), FLAG-2 shuffled beats 8/11 unique experiments, FLAG-3 ALL 6 follow-up scripts blocked by missing per-candle data (Critic wrong about Script 6), FLAG-4 abstention corrected to all 14 real=zero/negligible, FLAG-5 z=1.48. 5 visualization analyses from summary data: abstention sweep, experiment ranking, scale sensitivity, cross-pipeline comparison, accuracy-vs-Sharpe scatter. Verdict: stacking conclusively rejected, V3 Scheme B strictly superior. |
| local_analysis_builder | 2026-03-19 | builder | Follow-up analysis: 6 scripts + 5 FLAG corrections. ST-02=SC-03 (14 unique). Shuffled beats 8/11. ALL 6 follow-up scripts blocked (no per-candle data). Stacking conclusively rejected. |
| local_analysis_code_review | 2026-03-19 | critic | APPROVED: 0 blocks, 3 minor FLAGs. All 5 Critic FLAG corrections verified. Builder correctly caught Critic error on Script 6 (block bootstrap needs per-candle data, not summary stats). Scripts clean, visualizations well-designed, addendum comprehensive. Stacking conclusively rejected — 14 unique experiments, shuffled null beats 7/10, zero abstention, all Sharpe negative. V3 Scheme B strictly superior. Review at: pipeline_builds/stack-specialists_critic_analysis_code_review.md |
| local_analysis_report_build | 2026-03-19 | system | Building LaTeX report from stack-specialists_analysis_report.md |
| local_analysis_code_review | 2026-03-19 | critic | APPROVED 0 blocks 3 minor FLAGs |
| local_analysis_report_build | 2026-03-19 | system | Building LaTeX report from stack-specialists_analysis_report.md |
| local_analysis_code_review | 2026-03-19 | critic | In progress |
| local_analysis_code_review | 2026-03-19 | critic | APPROVED: 0 blocks, 3 minor FLAGs. All 5 Critic FLAG corrections verified. Review at: pipeline_builds/stack-specialists_critic_analysis_code_review.md |
| local_analysis_code_review | 2026-03-19 | critic | APPROVED with 3 low FLAGS (0 blocks). All 5 Critic FLAGs addressed: FLAG-1 ST-02=SC-03 confirmed (14 unique), FLAG-2 shuffled beats 7/10 unique, FLAG-3 ALL 6 scripts blocked (Critic wrong about Script 6), FLAG-4 abstention corrected, FLAG-5 z=1.48. Minor FLAGS: (1) Script 01 shuffled count not deduplicated, (2) Script 03 rounds z to 1.49 not 1.48, (3) addendum says 15 experiments in scatter description. All low-priority text precision issues. Stacking conclusively rejected. Review at: pipeline_builds/stack-specialists_critic_analysis_code_review.md |
| local_analysis_report_build | 2026-03-19 | system | Building LaTeX report from stack-specialists_analysis_report.md |
| local_analysis_code_review | 2026-03-19 | critic | APPROVED 3 low FLAGS 0 blocks. All 5 Critic FLAGs addressed. Stacking conclusively rejected. Review at: pipeline_builds/stack-specialists_critic_analysis_code_review.md |
| local_analysis_report_build | 2026-03-19 | builder | LaTeX report compiled: 11 pages, 512KB PDF with all tables, figures, and cross-pipeline analysis |
| local_analysis_complete | 2026-03-19 | system | Auto-completing local analysis. Moving to Phase 2. |

## Local Experiment Execution
_Status: Auto-triggered on Phase 1 completion_

Experiments run locally on the VPS via `run_experiment.py`. The pipeline auto-transitions:
`phase1_complete` → `experiment_running` → `experiment_complete` → Phase 2

- **Results:** `notebooks/local_results/stack-specialists/`
- **Manual trigger:** `R run stack-specialists`

### Experiment History
| Run | Date | Duration | Experiments | Errors | Notes |
|-----|------|----------|-------------|--------|-------|

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on experiment completion_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| phase2_architect_design | 2026-03-19 | architect | Phase 2 forensic close-out design: 8 experiments (2 forensic + 4 pivot + 2 baseline) × 3 folds = 24 runs. Forensic: block bootstrap CI + 1000x permutation test to formalize negative result with publication-quality statistics. Pivot: magnitude-mode specialists (HuberLoss δ=0.05) + GRU temporal stacker (h=16, lookback=5) to test whether fixing event→direction gap and adding temporal context changes outcome. V3 Scheme B actual replication as beat-this baseline. Expected outcome: all pivots fail, stacking confirmed dead, pipeline closed. Design at pipeline_builds/stack-specialists_phase2_architect_design.md |
| phase2_architect_design | 2026-03-20 | architect | Phase 2 forensic close-out design: 8 experiments × 3 folds = 24 runs. Block bootstrap CI + permutation test + magnitude-mode specialists + GRU stacker pivot. V3 Scheme B replication as baseline. Design at pipeline_builds/stack-specialists_phase2_architect_design.md |
| phase2_critic_design_review | 2026-03-20 | critic | APPROVED: 0 BLOCKs, 5 FLAGs (2 medium, 3 low). FLAG-1 (MED): P2-P-03 GRU stacker loss function unspecified for classification inputs — specify HuberLoss for consistency. FLAG-2 (MED): Magnitude specialist training ~180 samples for regression — overfitting risk, document limitation. FLAG-3 (LOW): P2-P-04 V3 Scheme B will produce 100% abstention — plan forced-trade metrics. FLAG-4 (LOW): Confirm specialist retraining per fold-holdout. FLAG-5 (LOW): Document block_size=20 choice. Clean forensic close-out design, disciplined scope. Review at: pipeline_builds/stack-specialists_phase2_critic_design_review.md |
| phase2_critic_design_review | 2026-03-20 | critic | APPROVED 0 blocks 5 flags. Forensic methodology sound (block bootstrap + permutation test). Pivot experiments well-controlled 2x2 factorial. FLAGS: (1) block_size sensitivity, (2) magnitude specialist distribution shift diagnostic, (3) GRU param/sample 3:1, (4) P2-P-04 abstention edge case, (5) per-candle predictions save. Checklist 12/14. Review at: pipeline_builds/stack-specialists_phase2_critic_design_review.md |
| phase2_critic_design_review | 2026-03-20 | critic | APPROVED 0 blocks 5 flags. Review at: pipeline_builds/stack-specialists_phase2_critic_design_review.md |
| phase2_builder_implementation | 2026-03-20 | builder | In progress |
| phase2_critic_design_review | 2026-03-20 | critic | APPROVED 0 blocks 5 flags. Review at: pipeline_builds/stack-specialists_phase2_critic_design_review.md |
| phase2_builder_implementation | 2026-03-20 | builder | In progress |
| phase2_critic_design_review | 2026-03-20 | critic | APPROVED 0 blocks 5 flags. Review at: pipeline_builds/stack-specialists_phase2_critic_design_review.md |
| phase2_builder_implementation | 2026-03-20 | builder | Phase 2 notebook built: 64 cells (28 code, 36 markdown), 8 experiments x 3 folds = 24 runs + 1000 permutations. Forensic: P2-F-01 block bootstrap (3-fold round-robin, block_size sensitivity {10,20,40}), P2-F-02 permutation test (1000x). Pivots: P2-P-01 magnitude LR, P2-P-02 magnitude GRU(h=16,L=5), P2-P-03 classification GRU (control), P2-P-04 V3 Scheme B replication. Baselines: majority + shuffled. All 5 Critic FLAGS addressed. Build script: build_stack_specialists_phase2.py. Committed 1c8db41. |
| phase2_critic_code_review | 2026-03-20 | critic | APPROVED: 0 BLOCKS, 4 FLAGS (all low-medium). Notebook faithfully implements all 8 experiments from Phase 2 design. All 5 design review FLAGS addressed. Block bootstrap, permutation test, magnitude specialists, GRU stacker, V3 Scheme B replication all correctly implemented. Statistical methodology sound. 3-fold round-robin is a major upgrade. 18/18 checklist items pass. Review: stack-specialists_phase2_critic_code_review.md |
| phase2_complete | 2026-03-20 | architect | Phase 2 COMPLETE. Critic code review APPROVED 18/18 checklist, 0 BLOCKs, 4 non-blocking FLAGS (all low-medium). All 8 experiments from forensic close-out design faithfully implemented: P2-F-01 block bootstrap CI (3-fold round-robin, block_size sensitivity {10,20,40}), P2-F-02 1000x permutation test, P2-P-01 magnitude+LR, P2-P-02 magnitude+GRU, P2-P-03 classification+GRU (control), P2-P-04 V3 Scheme B actual replication, P2-BL-01 majority, P2-BL-02 shuffled. All 5 design review FLAGS addressed. Builder correctly chose BCEWithLogitsLoss over HuberLoss for GRU stacker (semantically correct for binary direction). 64-cell notebook, 24 runs + 1000 permutations. Notebook ready for Colab execution. Expected outcome: Outcome A (all pivots fail, stacking confirmed dead, pipeline closed permanently). |

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
