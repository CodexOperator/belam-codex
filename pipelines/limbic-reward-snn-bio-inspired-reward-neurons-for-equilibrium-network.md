---
primitive: pipeline
status: phase1_review
priority: high
type: research
version: limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network
spec_file: machinelearning/snn_applied_finance/specs/limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network.ipynb
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
- **Spec:** `snn_applied_finance/specs/limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network.ipynb`
