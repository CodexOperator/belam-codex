---
primitive: pipeline
status: p1_architect_design
priority: high
type: research
version: snn-energy-topology-a1-energy-aware-neuron
spec_file: machinelearning/snn_applied_finance/specs/snn-energy-topology-a1-energy-aware-neuron_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_snn-energy-topology-a1-energy-aware-neuron.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [snn, research, neuron-architecture, energy-model]
project: snn-energy-topology-research
started: 2026-03-27
---

# Implementation Pipeline: SNN-ENERGY-TOPOLOGY-A1-ENERGY-AWARE-NEURON

## Description
A1: Energy-Aware LIF Neuron — Base Implementation. Pure PyTorch implementation of a leaky integrate-and-fire neuron with energy accounting. Energy costs: spike emission (high), spike reception (low). Energy earned: proportional to frequency match accuracy. Net energy tracked per neuron per batch. Weight clamping: 0.1-10 range. Surrogate gradient for backprop through spikes. Test with synthetic constant-frequency input (does neuron settle to stable energy-positive firing rate?) and synthetic varying-frequency input (does neuron adapt?). Code directory: machinelearning/snn_applied_finance/snn_energy_topology/. This is the foundation — all other subtasks depend on this neuron implementation.

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_snn-energy-topology-a1-energy-aware-neuron.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-27 | belam-main | Pipeline instance created |

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
- **Spec:** `snn_applied_finance/specs/snn-energy-topology-a1-energy-aware-neuron_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/snn-energy-topology-a1-energy-aware-neuron_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/snn-energy-topology-a1-energy-aware-neuron_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/snn-energy-topology-a1-energy-aware-neuron_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_snn-energy-topology-a1-energy-aware-neuron.ipynb`
