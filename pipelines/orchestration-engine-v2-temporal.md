---
primitive: pipeline
status: phase1_build
priority: medium
version: orchestration-engine-v2-temporal
spec_file: machinelearning/snn_applied_finance/specs/orchestration-engine-v2-temporal_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_orchestration-engine-v2-temporal.ipynb
agents: [architect, critic, builder]
tags: [orchestration, temporal, spacetimedb, autoclave, persistent-agents]
project: multi-agent-infrastructure
started: 2026-03-21
---

# Implementation Pipeline: ORCHESTRATION-ENGINE-V2-TEMPORAL

## Description
Orchestration Engine v2: Temporal state (SpacetimeDB), persistent agents, autoclave shared view, temporal handoffs

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_orchestration-engine-v2-temporal.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-21 | belam-main | Pipeline instance created |
| pipeline_created | 2026-03-21 | belam-main | Pipeline created: Orchestration Engine v2: Temporal state (SpacetimeDB), persistent agents, autoclave shared view, temporal handoffs |
| pipeline_created | 2026-03-21 | belam-main | Pipeline created: Orchestration Engine v2 temporal state, persistent agents, autoclave view |
| pipeline_created | 2026-03-21 | belam-main | Pipeline created |
| architect_design | 2026-03-21 | architect | Design complete: SpacetimeDB temporal overlay for V2 engine. 5 tables (pipeline_state, state_transition, handoff, agent_context, agent_presence), persistent agent context model, autoclave shared dashboard with time-travel, e0a coordinates. Overlay pattern — filesystem stays source of truth, ~30 line V2 diff, ~770 lines new code total. 5 open questions for critic. |
| architect_design | 2026-03-21 | architect | Design complete: SpacetimeDB temporal overlay for V2 engine |
| architect_design | 2026-03-21 | architect | Design complete: SpacetimeDB temporal overlay for V2 engine |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 5 FLAGs (2 high, 2 medium, 1 low), 4 suggestions. Overlay architecture and persistent agent context are excellent. FLAG-1 (HIGH): SpacetimeDB subscription model has no consumer — ephemeral agent sessions don't maintain connections for push notifications. Recommend SQLite+WAL as initial backing store (same Python API, zero new deps). FLAG-2 (HIGH): SQL injection in Python client f-string queries. FLAG-3 (MED): Reducer parameter passing convention mismatch — will fail at runtime. FLAG-4 (MED): Agent presence depends on after_tool_call hook infrastructure not yet deployed. FLAG-5 (LOW): STAGE_SEQUENCE divergence inherited from V2. Architect's 5 open questions answered. Review at: pipeline_builds/orchestration-engine-v2-temporal_critic_design_review.md |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 6 FLAGs (3 medium, 3 low), 5 suggestions. Temporal overlay design is sound — filesystem stays source of truth, SpacetimeDB is opt-in enhanced view with graceful degradation. FLAG-1 (MED): SQL injection in temporal_overlay.py queries. FLAG-2 (MED): complete_stage reducer signature mismatches Python client. FLAG-3 (MED): agent_context has no filesystem backup, violating source-of-truth principle. FLAG-4 (LOW): merge_json undefined. FLAG-5 (LOW): agent_presence no TTL. FLAG-6 (LOW): temporal_sync only covers pipeline_state. SpacetimeDB justified if subscriptions needed soon, otherwise SQLite simpler. Review at: pipeline_builds/orchestration-engine-v2-temporal_critic_design_review.md |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 6 FLAGs (3 med, 3 low). Review at: pipeline_builds/orchestration-engine-v2-temporal_critic_design_review.md |
| builder_implementation | 2026-03-21 | builder | In progress |

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
- **Spec:** `snn_applied_finance/specs/orchestration-engine-v2-temporal_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/orchestration-engine-v2-temporal_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/orchestration-engine-v2-temporal_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/orchestration-engine-v2-temporal_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_orchestration-engine-v2-temporal.ipynb`
