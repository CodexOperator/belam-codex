---
primitive: pipeline
status: p1_bugfix
priority: high
type: builder-first
version: git-diff-handoff-context
spec_file: machinelearning/snn_applied_finance/specs/git-diff-handoff-context_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_git-diff-handoff-context.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [snn, finance]
project: snn-applied-finance
started: 2026-03-25
archived: 2026-03-25
---

# Implementation Pipeline: GIT-DIFF-HANDOFF-CONTEXT

## Description
Add git-diff context to pipeline handoff messages — snapshot commit hashes at each stage transition, generate scoped diffs when building handoff context for returning agents

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_git-diff-handoff-context.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-25 | belam-main | Pipeline instance created |
| p1_builder_implement | 2026-03-25 | builder | Implemented handoff_diff.py with snapshot recording and scoped diff generation. Wired into pipeline_orchestrate.py complete/block flows. 17 tests all passing. |

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
- **Spec:** `snn_applied_finance/specs/git-diff-handoff-context_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/git-diff-handoff-context_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/git-diff-handoff-context_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/git-diff-handoff-context_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_git-diff-handoff-context.ipynb`
