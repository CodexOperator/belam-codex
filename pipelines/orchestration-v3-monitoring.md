---
primitive: pipeline
status: phase1_build
priority: medium
version: orchestration-v3-monitoring
spec_file: machinelearning/snn_applied_finance/specs/orchestration-v3-monitoring_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_orchestration-v3-monitoring.ipynb
agents: [architect, critic, builder]
tags: [orchestration, monitoring, v3, dashboard]
project: multi-agent-infrastructure
started: 2026-03-21
---

# Implementation Pipeline: ORCHESTRATION-V3-MONITORING

## Description
Orch V3: Real-time monitoring suite — .v namespace, SQLite WAL change detection, persona-scoped dashboard views, cascading dep resolution

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_orchestration-v3-monitoring.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-21 | belam-main | Pipeline instance created |
| pipeline_created | 2026-03-21 | belam-main | Launching Phase 1 |
| architect_design | 2026-03-21 | architect | Design complete: Option C hybrid architecture. 3 new files (monitoring_views.py, wal_watcher.py, dependency_graph.py), 3 modified files. .v namespace with 4 view types (turn-by-turn, live-diff, timeline, agent-context). Schema v2 migration adds pipeline_dependency + view_config tables. Cascading dep resolution hooks into _post_state_change. WAL polling at 2s intervals for human-facing canvas dashboard. ~950 lines new code. |
| architect_design | 2026-03-21 | architect | Design complete |
| architect_design | 2026-03-21 | architect | Design complete |
| architect_design | 2026-03-21 | architect | Design complete: Option C hybrid, 3 new files, .v namespace, schema v2 migration |
| architect_design | 2026-03-21 | architect | Design complete: Option C hybrid, 3 new files, .v namespace, schema v2 migration |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 5 FLAGs (2 med, 3 low). Design is sound, well-scoped, implementable. FLAG-1: cycle detection needs explicit visited set in resolve_downstream_deps. FLAG-2: VIEW_REGISTRY vs view_config dual source of truth. FLAG-3/4/5: minor cleanup items. |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 5 FLAGs (2 med, 3 low) |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 5 FLAGs |

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
- **Spec:** `snn_applied_finance/specs/orchestration-v3-monitoring_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/orchestration-v3-monitoring_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/orchestration-v3-monitoring_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/orchestration-v3-monitoring_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_orchestration-v3-monitoring.ipynb`
