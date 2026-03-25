---
primitive: pipeline
status: p1_builder_implement
priority: high
type: builder-first
version: setup-vectorbt-nautilus-pipeline-s1-environment-setup
spec_file: machinelearning/snn_applied_finance/specs/setup-vectorbt-nautilus-pipeline-s1-environment-setup_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_setup-vectorbt-nautilus-pipeline-s1-environment-setup.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [snn, finance]
project: snn-applied-finance
started: 2026-03-25
---

# Implementation Pipeline: SETUP-VECTORBT-NAUTILUS-PIPELINE-S1-ENVIRONMENT-SETUP

## Description
Install VectorBT PRO, NautilusTrader, supporting libs. Pin versions. Smoke test imports and trivial backtest.

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_setup-vectorbt-nautilus-pipeline-s1-environment-setup.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-25 | belam-main | Pipeline instance created |
| architect_design | 2026-03-25 | architect | Design v1: Validates and supplements the detailed task spec. Key decisions: (1) system-wide install with --break-system-packages (consistency with existing torch/snntorch/scipy stack, no venv). (2) VectorBT PRO graceful fallback to OSS vectorbt if no license. (3) NautilusTrader: pip first, Rust toolchain build if no ARM64 wheel. 4 deliverables (~130L): requirements-backtest.txt, directory structure, smoke tests, setup script. ARM64 risk assessment for all 8 packages. 4 open questions for critic (VectorBT license, system vs venv, NautilusTrader ARM64, separate requirements file). |

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
- **Spec:** `snn_applied_finance/specs/setup-vectorbt-nautilus-pipeline-s1-environment-setup_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/setup-vectorbt-nautilus-pipeline-s1-environment-setup_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/setup-vectorbt-nautilus-pipeline-s1-environment-setup_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/setup-vectorbt-nautilus-pipeline-s1-environment-setup_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_setup-vectorbt-nautilus-pipeline-s1-environment-setup.ipynb`
