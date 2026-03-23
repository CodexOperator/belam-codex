---
primitive: pipeline
status: local_analysis_in_progress
priority: high
type: research
version: limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network
spec_file: machinelearning/snn_applied_finance/specs/limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/crypto_limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network_predictor.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [snn, finance]
project: snn-applied-finance
started: 2026-03-23
---

# Implementation Pipeline: LIMBIC-REWARD-SNN-BIO-INSPIRED-REWARD-NEURONS-FOR-EQUILIBRIUM-NETWORK

## Description
limbic reward snn bio inspired reward neurons for equilibrium network

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-23 | belam-main | Pipeline instance created |
| architect_design | 2026-03-23 | architect | Design v1: LimbicRewardModule — differentiable reward modulation for equilibrium SNN. Energy pool tracks prediction quality, modulates loss landscape (amplify when confident, dampen when exploring) + LIF thresholds (lower when energy-rich, raise when energy-poor). 9 limbic variants + 3 baselines = 120 runs across 10 folds. Targets the dead-output-neuron problem and signal-starved regime. No RL needed — shaped loss via differentiable energy dynamics. ~6h CPU, ~1.5h GPU. 4 open questions for critic. |
| critic_design_review | 2026-03-23 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (2 HIGH, 1 MED, 1 LOW). FLAG-1 HIGH: torch.sign() has zero gradient — reward pathway not differentiable, use tanh(k=10). FLAG-2 HIGH: energy batch semantics need specification — recommend per-batch-mean. FLAG-3 MED: inference behavior unspecified. FLAG-4 LOW: cumulative DSR. Core thesis sound, ablation matrix clean, evaluation rigorous. Review at: pipeline_builds/limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network_critic_design_review.md |
| builder_implementation | 2026-03-23 | builder | Notebook built: 52 cells (24 code, 28 markdown, 65K chars). PhasicEquilibriumSNN backbone (EQ-ABL-02 phasic-only, 14 input dims, single output). LimbicRewardModule with differentiable reward (FLAG-1: tanh(k=10)), per-batch-mean energy (FLAG-2), frozen inference energy (FLAG-3). 9 experiments (LR-BASE through LR-08) + 3 baselines (majority, logistic, GRU). TBPTT training with energy-modulated loss + threshold. Full analysis: statistical tests (t-test, bootstrap CI, paired, DSR with both n=12 and n=215), ablation decomposition, break-even costs, 6 diagnostic plots (energy trajectories, final energy boxplot, spike rates, prediction entropy, reward gradient norms, Sharpe comparison). All 4 Critic FLAGs and 4 Suggestions addressed. |
| critic_code_review_blocked | 2026-03-23 | critic | BLOCKED: BLOCK-1: Energy graph accumulation causes RuntimeError on TBPTT chunk 2+. LimbicRewardModule.update_energy_batch() creates energy tensor with grad_fn connecting to batch_preds (from model forward). Next chunk uses this energy in loss via get_modulation(). Backward tries to traverse through freed graph from previous chunk. Fix: add self.energy = self.energy.detach() after clamp in update_energy_batch(). Also add documentation comment that reward_sensitivity/cost_sensitivity are non-learnable with detach. All 4 design FLAGs resolved correctly (tanh k=10, batch-mean energy, frozen inference, cumulative DSR). 2 additional FLAGs (1 MED patience float, 1 LOW DSR pass). |
| builder_apply_blocks | 2026-03-23 | builder | BLOCK-1 fix applied (3 changes + 1 documentation fix): (1) Added self.energy = self.energy.detach() after clamp in update_energy_batch() — prevents graph accumulation across TBPTT chunks. (2) Added comment documenting reward_sensitivity/cost_sensitivity are non-learnable with detach. (3) Updated S2 reward gradient norm plot title to note expected ≈0 values. (4) Updated builder notes in Cell 2 to reflect detach behavior. Also addressed MED FLAG: improved patience_counter += 0.5 comment to document 50-epoch implication. |
| critic_code_review | 2026-03-23 | critic | APPROVED: BLOCK-1 fix verified. All 4 changes applied correctly: (1) self.energy = self.energy.detach() prevents graph accumulation across TBPTT chunks, (2) non-learnable parameter documentation, (3) S2 plot title updated, (4) patience comment clarified. All 4 original design FLAGs remain resolved. Notebook ready for Colab execution. |
| phase1_complete | 2026-03-23 | architect | Phase 1 COMPLETE. Critic code review APPROVED after BLOCK-1 fix (energy.detach() for TBPTT graph accumulation). All 4 design FLAGs resolved. 29-cell notebook: LimbicRewardModule (differentiable energy pool + loss/threshold modulation), 9 limbic variants + 3 baselines = 120 runs across 10 folds. ~6h CPU, ~1.5h GPU. Key fix: energy state must be detached between TBPTT chunks to prevent unbounded computation graph growth. Notebook ready for Colab execution. Awaiting Shael review for Phase 2 direction. |
| local_experiment_running | 2026-03-23 | system | Experiment run started (PID: 2842116, mode: supervised) |
| local_experiment_running | 2026-03-23 | system | Experiment run started (PID: 2842351, mode: supervised) |
| local_experiment_running | 2026-03-23 | builder | RESULTS: 12 experiments (9 SNN + 3 baselines), dry-run CPU with synthetic data. All SNN variants (LR-BASE through LR-08) produce identical results: acc=50.4%, SR=+0.46, turnover=0.0, entropy=1.0. Limbic modulation has ZERO observable effect — consistent with energy-detach pattern (reward_sensitivity receives no gradient). Model converges to constant prediction on 5 epochs/synthetic data. BL-02 (logistic) best acc 53.0%. Bug fixed: snntorch threshold is Buffer, requires fill_() not float assignment. Needs real data + full epochs for meaningful limbic comparison. |
| local_analysis_architect | 2026-03-23 | system | Local analysis started. Results at machinelearning/snn_applied_finance/notebooks/local_results/limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network/ |
| local_analysis_architect | 2026-03-23 | architect | TOTAL FAILURE — limbic module has zero effect. All 9 variants identical to baseline. Root cause: dead neurons by epoch 2 (spike rate = 0.0 in both layers). With zero spikes, predictions are near-zero, reward is ~1e-6, reward gradient is exactly 0.0. The limbic module receives no gradient and learns nothing. Energy dynamics work mechanically (pool decays, bounds clamp correctly) but modulate nothing. Only 5 epochs ran (vs designed 100). The equilibrium SNN backbone (96→48, T=1) dies on CPU — wrong backbone choice. Limbic must be re-tested on V3 Scheme B (128→64, T=20) which actually produces 53.5% accuracy. 4 follow-up scripts specified. |
| local_experiment_running | 2026-03-23 | system | Experiment completed (all 12 results PKLs present). Dead-PID recovery — transitioning to experiment_complete for analysis auto-kick. |
| local_analysis_architect | 2026-03-23 | system | Local analysis started. Results at machinelearning/snn_applied_finance/notebooks/local_results/limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network/ |
| local_analysis_architect | 2026-03-23 | system | Local analysis started. Results at machinelearning/snn_applied_finance/notebooks/local_results/limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network/ |

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on Phase 1 completion_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| phase2_architect_design_blocked | 2026-03-23 | architect | BLOCKED: BLOCK: No Phase 2 direction from Shael. Phase 2 is the human-in-the-loop phase — requires Shael's feedback on Phase 1 results before design can proceed. The notebook hasn't been run yet (awaiting Colab execution). Phase 2 design needs: (1) Phase 1 experiment results, (2) Shael's analysis and direction. Unblock by creating pipeline_builds/limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network_phase2_direction.md with Shael's feedback. |

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
- **Spec:** `snn_applied_finance/specs/limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network.ipynb`
