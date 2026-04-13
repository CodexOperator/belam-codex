---
primitive: pipeline
status: archived
archived: 2026-03-21
priority: critical
version: orchestration-engine-v1
spec_file: machinelearning/snn_applied_finance/specs/orchestration-engine-v1_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_orchestration-engine-v1.ipynb
agents: [architect, critic, builder]
tags: [orchestration, engine, infrastructure, v1]
project: multi-agent-infrastructure
started: 2026-03-21
pending_action: builder_implementation
current_phase: 
dispatch_claimed: false
last_updated: 2026-03-21 10:02
reset: false
---
# Implementation Pipeline: ORCHESTRATION-ENGINE-V1

## Description
Unified orchestration engine via e0 coordinates, replacing legacy scripts

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_orchestration-engine-v1.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-21 | belam-main | Pipeline instance created |
| pipeline_created | 2026-03-21 | belam-main | Pipeline created: Unified orchestration engine via e0 coordinates, replacing legacy scripts |
| architect_design | 2026-03-21 | architect | Design complete: unified orchestration_engine.py architecture. Gap analysis shows ~70% built, ~1210 lines to inline from 3 legacy scripts. 10-step builder spec with testing checklist. Dependency inversion eliminates circular imports. F-label diffs for codex supermap. Hook integration as stretch goal. Coordinate interface fully specified. |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (2 medium, 2 low), 3 suggestions. Infrastructure refactoring design is solid. Dependency inversion correct, gap analysis verified against actual code. FLAG-1 (MED): Import STAGE_TRANSITIONS from pipeline_update.py instead of inlining — avoids dual maintenance. FLAG-2 (MED): Testing checklist missing error path coverage (missing state JSON, agent wake timeout, concurrent dispatch). FLAG-3 (LOW): F-label format inconsistency (D vs delta). FLAG-4 (LOW): Hook integration listed as stretch goal but appears mandatory in builder spec — clarify. Architect's open questions answered: Q1 import not inline, Q2 hooks as V1.1, Q3 warn every call. Review at: pipeline_builds/orchestration-engine-v1_critic_design_review.md |
| architect_design | 2026-03-21 | architect | Design complete: unified orchestration_engine.py architecture. 70% built, 10-step builder spec, dependency inversion, F-label diffs, e0 coordinate interface. |
| critic_design_review | 2026-03-21 | critic | In progress |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (2 med, 2 low). Dependency inversion correct, gap analysis verified. FLAG-1 MED: Import STAGE_TRANSITIONS not inline. FLAG-2 MED: Test checklist missing error paths. FLAG-3 LOW: F-label format. FLAG-4 LOW: Hook scope ambiguity. Review at: pipeline_builds/orchestration-engine-v1_critic_design_review.md |

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
- **Spec:** `snn_applied_finance/specs/orchestration-engine-v1_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/orchestration-engine-v1_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/orchestration-engine-v1_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/orchestration-engine-v1_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_orchestration-engine-v1.ipynb`
