---
primitive: pipeline
status: phase1_code_review
priority: critical
version: orchestration-engine-v2
spec_file: machinelearning/snn_applied_finance/specs/orchestration-engine-v2_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_orchestration-engine-v2.ipynb
agents: [architect, critic, builder]
tags: [orchestration, engine, infrastructure, v1]
project: multi-agent-infrastructure
started: 2026-03-21
---

# Implementation Pipeline: ORCHESTRATION-ENGINE-V2

## Description
Unified orchestration engine via e0 coordinates, replacing legacy scripts

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_orchestration-engine-v2.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-21 | belam-main | Pipeline instance created |
| pipeline_created | 2026-03-21 | belam-main | Pipeline created: Unified orchestration engine via e0 coordinates, replacing legacy scripts |
| architect_design | 2026-03-21 | architect | test |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (3 medium, 1 low), 4 suggestions. Architecture clean, V1 consolidation well-planned. FLAG-1 (MED): STAGE_TRANSITIONS import-vs-replace contradiction in Sections 4.3 vs 12.2 — must import not replace. FLAG-2 (MED): Gate coordinate references fragile under archival — use version strings for stored conditions. FLAG-3 (MED): pre/post_actions execution responsibility ambiguous between engine and coordinator. FLAG-4 (LOW): PID-based lock staleness won't work with OpenClaw process model — use timeout-based. S-03: e0_dispatch plugin's ctx.spawnAgent doesn't exist in OpenClaw API. Review at: pipeline_builds/orchestration-engine-v2_critic_design_review.md |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (3 med, 1 low). Review at: pipeline_builds/orchestration-engine-v2_critic_design_review.md |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (3 med, 1 low). Review at: pipeline_builds/orchestration-engine-v2_critic_design_review.md |
| builder_implementation | 2026-03-21 | builder | All 4 Critic FLAGs addressed in orchestration_engine.py (2043→2327 lines). FLAG-1: STAGE_TRANSITIONS import verified. FLAG-2: Declarative gate conditions with version-string refs + archival warning for coordinates. FLAG-3: pre/post_actions marked as metadata-only, coordinator relays spawn{} only. FLAG-4: Timeout-primary lock staleness, PID as secondary hint. Also: enhanced task prompts with full memory protocol, launch/archive CLI commands, knowledge file detection. |

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
- **Spec:** `snn_applied_finance/specs/orchestration-engine-v2_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/orchestration-engine-v2_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/orchestration-engine-v2_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/orchestration-engine-v2_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_orchestration-engine-v2.ipynb`
