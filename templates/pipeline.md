---
primitive: pipeline
name: Implementation Pipeline
description: >
  Generic 3-phase implementation pipeline for any notebook version.
  Phase 1: Autonomous build (architect → critic → builder).
  Phase 2: Human-in-the-loop (Shael feedback → revision → rebuild).
  Phase 3: Iterative research (gated on phase 2 completion, scored proposals).
  Create one instance per notebook version: pipelines/{version}.md
fields:
  status:
    type: string
    required: true
    default: phase1_design
    enum: [phase1_design, phase1_critique, phase1_revision, phase1_build, phase1_code_review, phase1_complete, phase2_feedback, phase2_revision, phase2_rebuild, phase2_code_review, phase2_complete, phase3_proposed, phase3_approved, phase3_build, phase3_code_review, phase3_complete, archived]
  priority:
    type: string
    enum: [critical, high, medium, low]
  version:
    type: string
    required: true
    description: "Notebook version key (v1, v2, v3, v4, ...)"
  spec_file:
    type: string
  output_notebook:
    type: string
  agents:
    type: string[]
    description: "Agent IDs involved in this pipeline"
  tags:
    type: string[]
  project:
    type: string
    description: "Parent project primitive"
  started:
    type: date
  phase1_completed:
    type: date
  phase2_completed:
    type: date
  phase3_iterations:
    type: object[]
    description: "Array of phase 3 iteration records: [{id, hypothesis, justification, proposed_by, proposed_at, status, result_summary}]"
  phase3_gate:
    type: string
    default: phase2_complete
    description: "Phase 3 iterations only unlock after this status is reached"
  artifacts:
    type: object
    description: "Paths to pipeline artifacts (design, review, notebook)"
---

# Implementation Pipeline: {version}

## Description
_{What this notebook version explores}_

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on Phase 1 completion_

### Feedback
_(Shael's feedback goes here when provided)_

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
- **Spec:** `snn_applied_finance/specs/{version}_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/{version}_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/{version}_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/{version}_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_{version}.ipynb`
