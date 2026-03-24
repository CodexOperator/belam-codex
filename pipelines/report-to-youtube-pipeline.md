---
primitive: pipeline
status: architect_design
priority: high
type: infrastructure
version: report-to-youtube-pipeline
agents: [architect, critic, builder]
supersedes:
tags: [snn, finance]
project: snn-applied-finance
started: 2026-03-24
---

# Implementation Pipeline: REPORT-TO-YOUTUBE-PIPELINE

## Description
Publish research reports and analysis directly to YouTube as narrated video content

## Type
Infrastructure pipeline — no notebook, no experiment. Deliverables are code, hooks, plugins, and config files.
At phase1_complete, this pipeline is ready for human review and archival (no experiment/analysis phases).

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-24 | belam-main | Pipeline instance created |

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
- **Spec:** `snn_applied_finance/specs/report-to-youtube-pipeline_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/report-to-youtube-pipeline_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/report-to-youtube-pipeline_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/report-to-youtube-pipeline_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_report-to-youtube-pipeline.ipynb`
