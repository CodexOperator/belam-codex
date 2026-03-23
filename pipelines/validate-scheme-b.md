---
primitive: pipeline
status: phase2_build
priority: high
version: validate-scheme-b
spec_file: machinelearning/snn_applied_finance/specs/validate-scheme-b_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/crypto_validate-scheme-b_predictor.ipynb
agents: [architect, critic, builder]
tags: [validation, statistics, snn]
project: snn-applied-finance
started: 2026-03-17
version_label: v5-validation
---

# Implementation Pipeline: VALIDATE-SCHEME-B

## Description
Statistical validation of V3 Scheme B (+0.45 Sharpe) with 7+ walk-forward folds to establish significance

## Notebook Convention
**All phases live in a single notebook** (`crypto_validate-scheme-b_predictor.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

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
| phase1_revision_architect | 2026-03-19 | coordinator | In progress |
| phase1_revision_architect | 2026-03-19 | architect | Revised design: 3 changes from coordinator direction. R1: V4 counterfactual comparison section (97.9% dead-network stats, membrane vs spike-count table, gradient flow diagram). R2: Membrane readout elevated to KEY FINDING in discussion (hierarchy of factors, biological analogy, design rule). R3: Double-confirmation verdict (positive + negative evidence = causal confidence). No changes to training/eval/stats. DSR Lo adjustment confirmed correct. ~6-8 new cells. |
| phase1_revision_architect | 2026-03-19 | architect | Revised design v2: R1 V4 counterfactual, R2 membrane readout KEY FINDING, R3 double-confirmation verdict |
| phase1_revision_architect | 2026-03-19 | architect | Revised design v2 |
| phase1_revision_architect | 2026-03-19 | architect | Revised design v2: R1 V4 counterfactual, R2 membrane readout KEY FINDING, R3 double-confirmation verdict |
| phase1_revision_critic_review | 2026-03-19 | critic | APPROVED with 3 FLAGS (0 blocks). All 3 coordinator direction points addressed: R1 V4 counterfactual (FLAG-1: document confounds - V4 also had learnable_scale), R2 membrane readout KEY FINDING (FLAG-2: escape hatch threshold 0.1-0.3 is untested hypothesis), R3 double-confirmation verdict (FLAG-3: clarify DOUBLY VALIDATED is interpretive not formal statistical test). Core validation pipeline UNCHANGED and correct. All 12 prior flags from v1/v2 confirmed resolved. Checklist 12/14. Review at: pipeline_builds/validate-scheme-b_critic_revision_review.md |
| phase1_revision_critic_review | 2026-03-19 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (all language precision). FLAG-1: V4 not single-variable change, temper causal claim. FLAG-2: membrane readout is necessary not sufficient. FLAG-3: use convergent evidence not causal-level. Review at validate-scheme-b_critic_revision_review.md |
| phase1_revision_critic_review | 2026-03-19 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (language precision). FLAG-1: temper V4 causal claim. FLAG-2: necessary not sufficient. FLAG-3: convergent evidence not causal-level. |
| phase1_revision_builder | 2026-03-19 | builder | Revised notebook v2: 58 cells (29 code, 29 markdown). 6 new cells added. Section 6.5: V4 Counterfactual (load V4 stats, side-by-side comparison table, gradient flow diagram, counterfactual verdict). Discussion: Membrane Readout KEY FINDING (hierarchy of factors, biological analogy, design rule for SNN finance). Combined Verdict: Convergent Evidence Assessment (positive + negative evidence). All 3 Critic Revision FLAGs addressed: FLAG-1 'primary architectural difference' with confounds documented, FLAG-2 'necessary' not 'necessary AND sufficient', FLAG-3 'VALIDATED with CONVERGENT EVIDENCE' not 'DOUBLY VALIDATED'. No existing cells modified (training/eval/stats frozen). Committed 98df761. |
| phase1_revision_builder | 2026-03-19 | builder | Revised notebook v2: 58 cells (29 code, 29 markdown). 6 new cells. V4 Counterfactual, Membrane Readout KEY FINDING, Convergent Evidence Verdict. All 3 Critic FLAGs addressed. Committed 98df761. |
| phase1_revision_code_review | 2026-03-19 | critic | APPROVED with 1 minor FLAG (0 blocks). All 3 revision FLAGs addressed: FLAG-1 confounds documented, FLAG-2 necessary not sufficient, FLAG-3 convergent evidence. No existing cells modified. 6 new cells verified: V4 stats loading with pkl dedup, side-by-side comparison, gradient flow diagram, counterfactual verdict, membrane readout discussion, convergent evidence assessment. Variable scope correct. 9/9 checklist pass. Review at: pipeline_builds/validate-scheme-b_critic_revision_code_review.md |
| phase1_complete | 2026-03-19 | architect | Phase 1 revision COMPLETE. Critic revision code review APPROVED 9/9, 0 blocks, 1 minor non-blocking FLAG (cell 50 else-branch language — won't trigger since V4 dead rate=97.9%). All 3 coordinator direction points verified: R1 V4 counterfactual comparison (hardcoded stats + pkl fallback, side-by-side table, gradient flow diagram, quasi-experimental verdict), R2 membrane readout elevated to KEY FINDING (hierarchy-of-factors table, biological analogy, design rule), R3 convergent evidence verdict (four-way matrix: positive+negative→VALIDATED WITH CONVERGENT EVIDENCE). All 3 critic revision FLAGs addressed: FLAG-1 confounds documented, FLAG-2 necessary not sufficient, FLAG-3 convergent evidence language. No existing cells modified. 58-cell notebook (51 original + 6 new + 1 updated notes cell). Notebook ready for Shael review. |
| local_experiment_running | 2026-03-19 | system | Local experiment run started (PID: 2569411) |
| local_experiment_running | 2026-03-19 | system | EXPERIMENT FAILED after 1 attempts: Process exited with code 1 |
| local_experiment_running | 2026-03-19 | system | Experiment run started (PID: 2579811, mode: supervised) |
| local_experiment_running | 2026-03-19 | system | Experiments complete. Results at machinelearning/snn_applied_finance/notebooks/local_results/validate-scheme-b |
| local_analysis_architect | 2026-03-19 | system | Local analysis started. Results at machinelearning/snn_applied_finance/notebooks/local_results/validate-scheme-b/ |
| local_analysis_architect | 2026-03-19 | architect | Analysis report complete. VERDICT: MIXED — signal confirmed, profitability unproven, abstention broken. Accuracy lift is REAL (t=4.80, p=0.001, 9/10 folds). Abstention 100% broken in all folds. Net Sharpe +0.40 NOT significant (p=0.49). Gross Sharpe reliably positive (20/20 folds). Turnover is the Sharpe killer (r=0.83 with gap). Temporal degradation significant (r=-0.71, p=0.02). Run incomplete (3/12 experiments). 6 additional analysis scripts specified. |
| local_analysis_architect | 2026-03-19 | architect | Analysis complete. Signal real (p=0.001), abstention broken, Sharpe NS. 6 scripts specified. |
| local_analysis_critic_review | 2026-03-19 | critic | APPROVED: 0 BLOCKs, 5 FLAGs. Core findings verified against raw pkl: accuracy lift real (t=4.80, p=0.001 confirmed), 100% abstention confirmed, net Sharpe NS (p=0.49 confirmed), gross Sharpe 20/20 positive. FLAGS: (1) Section 6.1 reports net_sharpe_full r=-0.71 but labels it gross Sharpe (actual gross r=-0.65), (2) 4/10 positive Sharpe folds not 5/10, (3) turnover bucket fold assignments wrong (corrected buckets strengthen the narrative), (4) VSB-03 stale (7 folds now vs 3 in report), (5) training dynamics plot from wrong pipeline. Statistical hygiene 10/10. Review at: validate-scheme-b_critic_local_analysis_review.md |
| local_analysis_critic_review | 2026-03-19 | critic | APPROVED: 0 BLOCKs, 5 FLAGs. Core findings verified. Review at validate-scheme-b_critic_local_analysis_review.md |
| local_analysis_critic_review | 2026-03-19 | critic | APPROVED |
| local_analysis_builder | 2026-03-20 | builder | Full 12-experiment analysis (120 records, 12 exp x 10 folds). All 5 Critic FLAGs fixed: FLAG-1 temporal degradation gross vs net labels, FLAG-2 positive folds=4/10, FLAG-3 turnover bucket assignments corrected, FLAG-4 VSB-03 updated to 10 folds, FLAG-5 training dynamics plot regenerated. 0/6 Architect scripts executable (all blocked by missing per-candle data). 8 supplementary analyses + 5 visualizations + LaTeX PDF (157KB). KEY: CTRL-01 (Scheme 0) has higher accuracy lift than VSB-01 — signal is feature-based. Abstention ~30% not 100% and hurts performance. |
| local_analysis_builder | 2026-03-20 | builder | Full 12-experiment analysis (120 records). 5/5 Critic FLAGs fixed. 0/6 Architect scripts blocked (no per-candle data). 8 supplementary analyses, 5 visualizations, LaTeX PDF. KEY: CTRL-01 (Scheme 0) beats VSB-01 on accuracy — signal is feature-based. Abstention ~30% not 100% and hurts. |
| local_analysis_code_review | 2026-03-20 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (2 medium, 2 low). All 5 prior FLAGs verified fixed. 120-record analysis (12 exp × 10 folds) correctly analyzed. Code quality high: deterministic seeds, proper scipy APIs, matplotlib standards. FLAG-1 (MED): '100% abstention error' framing is misleading — data changed between GPU/CPU runs, not original error. FLAG-2 (MED): 'signal is feature-based' claim needs paired test (p=0.048, barely significant; delta encoding has execution advantage not captured by accuracy). FLAG-3 (LOW): turnover-Sharpe correlation now p=0.093 (NS), narrative overstates evidence. FLAG-4 (LOW): abstention harms because |prediction magnitude| ≠ confidence (active_accuracy < accuracy in multiple folds). Review at: validate-scheme-b_critic_local_analysis_code_review.md |
| local_analysis_report_build | 2026-03-20 | system | Building LaTeX report from validate-scheme-b_analysis_report.md |
| local_analysis_report_build | 2026-03-20 | system | LaTeX report built. PDF: machinelearning/snn_applied_finance/notebooks/local_results/validate-scheme-b/validate-scheme-b_report.pdf (512.2 KB) |

## Local Experiment Execution
_Status: Auto-triggered on Phase 1 completion_

Experiments run locally on the VPS via `run_experiment.py`. The pipeline auto-transitions:
`phase1_complete` → `experiment_running` → `experiment_complete` → Phase 2

- **Results:** `notebooks/local_results/validate-scheme-b/`
- **Manual trigger:** `R run validate-scheme-b`

### Experiment History
| Run | Date | Duration | Experiments | Errors | Notes |
|-----|------|----------|-------------|--------|-------|

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on experiment completion_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| phase2_architect_design | 2026-03-23 | architect | Phase 2 design: 15 experiments (3 turnover reduction + 2 position sizing + 1 combined) × 10 folds = 140 runs. Only 30 require retraining (TURN-01 loss penalty). Rest reuse Phase 1 saved predictions via post-processing. Attack turnover (proven bottleneck r=0.83) and position sizing (binary→continuous). Break-even cost analysis for all variants. 4 open questions for critic. |
| phase2_critic_design_review | 2026-03-23 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (1 HIGH, 1 MED, 1 LOW). FLAG-1 HIGH: per-candle predictions NOT saved in Phase 1 pickle — builder must re-run VSB-02 with prediction saving before post-processing experiments (+1-2h, total ~4-5h vs architect's 3.5h). FLAG-2 MED: TURN-01 (loss modification) must be reported in separate tier from post-processing experiments. FLAG-3 LOW: Kelly sizing — use training-fold stats only. Experimental design is sound — directly attacks turnover bottleneck (r=0.82, p=0.004). Review at: pipeline_builds/validate-scheme-b_phase2_critic_design_review.md |

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
- **Notebook:** `snn_applied_finance/notebooks/crypto_validate-scheme-b_predictor.ipynb`
