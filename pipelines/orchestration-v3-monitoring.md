---
primitive: pipeline
status: phase2_in_progress
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
| builder_implementation | 2026-03-21 | builder | Implementation complete: 3 new files (monitoring_views.py 619L, dependency_graph.py 442L, wal_watcher.py 374L). Schema v2 migration with pipeline_dependency + view_config tables. Engine CLI: view, deps, watcher commands. All 5 Critic FLAGs addressed. |
| builder_implementation | 2026-03-21 | builder | Implementation complete: 3 new files, schema v2 migration, all 5 FLAGs addressed |
| builder_implementation | 2026-03-21 | builder | V3 implementation complete: 3 new files, schema v2, all 5 FLAGs addressed |
| critic_code_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (1 med, 3 low). All 5 design FLAGs addressed. New flags: heartbeat_extended overwrites session_id col with JSON blob (med), render_live_diff uses private _get_conn (low), HTML stats unescaped (low), compute_f_r_causal_chain is placeholder (low). |

## Phase 2: Human-in-the-Loop
_Status: Scoped — Shael directed scope 2026-03-22_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| phase2_architect_design | 2026-03-22 | architect | In progress |

### Feedback — Shael (2026-03-22 03:14 UTC)

**Core directive: Script-led, not agent-led orchestration.**

The orchestration script is the **pilot**. Agents are **engines/thrusters** — they provide power and execution, but the script decides trajectory, sequencing, and coordination. This is a critical architectural distinction:

- The script holds the execution graph, makes dispatch decisions, manages handoffs, detects stalls, and drives recovery
- Agents receive scoped work packages, execute, and report back — they don't decide what to do next
- The script's decisions flow through as R-label updates in the live view system, giving the observing agent (or human) a **temporal resonance** — you can feel the rhythm of orchestration through the update stream
- With the render engine (codex-engine-v3 Phase 2) providing live diff views, the script's R-label trail becomes a real-time narrative of what the system is doing and why
- Full agentic control is preserved *through* the view layer — the agent sees what the script is doing via R-labels and can intervene, steer, or override, but the script is the default authority for routine orchestration

**Phase 2 should strengthen this pattern:** make the script smarter about dispatch, sequencing, and recovery so agents need to intervene less. The monitoring views (.v namespace) become the communication channel between the script-pilot and the agent-observer.

### Additional Phase 2 Items
- Address non-blocking FLAGs from Phase 1 code review (heartbeat_extended session_id, render_live_diff _get_conn, HTML stats escaping, f_r_causal_chain placeholder)
- Integrate with render engine's live diff system (when available)
- Script-driven dispatch improvements (smarter sequencing, better stall detection thresholds)

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
