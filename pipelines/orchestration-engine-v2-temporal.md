---
primitive: pipeline
status: archived
priority: medium
version: orchestration-engine-v2-temporal
spec_file: machinelearning/snn_applied_finance/specs/orchestration-engine-v2-temporal_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_orchestration-engine-v2-temporal.ipynb
agents: [architect, critic, builder]
tags: [orchestration, temporal, spacetimedb, autoclave, persistent-agents]
project: multi-agent-infrastructure
started: 2026-03-21
archived: 2026-03-22
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
| builder_implementation | 2026-03-21 | builder | V2-temporal overlay: 3 new files (temporal_schema.py 262L, temporal_overlay.py 965L, temporal_sync.py 327L) + 68 lines V2 integration. SQLite+WAL backing (Critic S-01: no Rust on ARM64). All 6 Critic FLAGs addressed: FLAG-1 parameterized SQL, FLAG-2 split log_transition/advance_pipeline/create_handoff, FLAG-3 SQLite IS filesystem backup, FLAG-4 deep merge semantics defined, FLAG-5 presence TTL at query time, FLAG-6 reconciliation scope documented. Autoclave dashboard + timeline + time-travel + duration analytics + persistent agent context with dispatch injection. Commit 124658ad. |
| critic_code_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (1 medium, 3 low). All 6 design review FLAGs verified fixed. SQLite+WAL pivot correct. Parameterized SQL throughout, merge_json deep merge working, separated log/advance/handoff per FLAG-2, TTL at query time per FLAG-5, reconciliation scope documented per FLAG-6. New FLAG-1 (MED): record_transition() atomicity broken by nested commits — dead code, recommend removal. FLAG-2 (LOW): dashboard column truncation cosmetic. FLAG-3 (LOW): sync field mapping incomplete (pending_action vs current_stage). FLAG-4 (LOW): temporal records in legacy orchestrate path may have slight inference errors. Review at: pipeline_builds/orchestration-engine-v2-temporal_critic_code_review.md |
| phase1_complete | 2026-03-21 | architect | Phase 1 COMPLETE. Critic code review APPROVED: 0 BLOCKs, 4 non-blocking FLAGs (1 med, 3 low). All 6 design review FLAGs verified fixed. SQLite+WAL pivot from SpacetimeDB was correct (no Rust on ARM64, no subscription consumers). Deliverables: temporal_schema.py (262L), temporal_overlay.py (965L), temporal_sync.py (327L) + 68L V2 integration. Overlay pattern works as designed — V2 continues normally, temporal capabilities degrade gracefully. FLAG-1 (MED): record_transition() is dead code with false atomicity claim — recommend removal in Phase 2. FLAGs 2-4 are cosmetic/minor. Ready for Phase 2 human review. |
| critic_code_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (1 med, 3 low). All 6 design FLAGs fixed. Review at: pipeline_builds/orchestration-engine-v2-temporal_critic_code_review.md |
| phase1_complete | 2026-03-21 | belam-main | Advancing to Phase 2 with Shael direction file |

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on Phase 1 completion_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| phase2_architect_design | 2026-03-21 | architect | Phase 2 design per Shael direction file |
| phase2_architect_design | 2026-03-21 | architect | Phase 2 design complete: R1 F-label/R-label causal coupling via time_travel_revert() with ⮌ format and r_label_hint. R2 persona-filtered dashboard views (i1=architect, i2=critic, i3=builder) via get_dashboard(persona=), set by orchestration in dispatch payload. FLAG-1 record_transition() deletion. 10-step builder spec, 17-item test checklist, 5 design decisions, 4 open questions for critic. |
| phase2_architect_design | 2026-03-21 | architect | Phase 2 design complete |
| phase2_architect_design | 2026-03-21 | architect | Phase 2 design complete: F-label/R-label causal coupling, persona-filtered dashboard views, FLAG-1 removal |
| phase2_critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (1 med, 2 low). R1 causal coupling aligned, R2 persona views all 5 sub-reqs met, FLAG-1 deletion safe. Med FLAG: time_travel() returns transition not state - clarify for builder. |
| phase2_critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (1 med, 2 low) |
| phase2_builder_implementation | 2026-03-21 | builder | In progress |
| phase2_builder_implementation | 2026-03-21 | builder | Phase 2 implementation complete: R1 time_travel_revert() with F-label ⮌ format and R-label hints for causal coupling. R2 persona-filtered dashboards (get_dashboard(persona=), format_dashboard_for_prompt(), PERSONA_STAGE_FILTERS, dispatch payload integration). FLAG-1 record_transition() deleted. FLAG-2 dynamic column widths. FLAG-3 sync field mapping. All 3 Critic Phase 2 FLAGs addressed. 17/17 test checklist passed. temporal_overlay.py +424L, orchestration_engine.py +153L, temporal_sync.py +21L. Commit 911870b0. |
| phase2_builder_implementation | 2026-03-21 | builder | Phase 2 implementation complete: time_travel_revert() with F/R label causal coupling (⮌ format F-labels + r_label_hint for cockpit re-render), persona-filtered dashboard views (get_dashboard(persona=), format_dashboard_for_prompt(), PERSONA_STAGE_FILTERS), handle_revert() CLI with cross-phase guard, DispatchPayload view_filter injection. Dead code removed, cross-phase visibility fixed, dynamic column widths. 21/21 tests pass. |
| phase2_builder_implementation | 2026-03-21 | builder | Phase 2 complete: F/R coupling, persona views, dead code removal. 21/21 tests pass. |
| phase2_builder_implementation | 2026-03-21 | builder | Phase 2 complete: F/R coupling, persona views, dead code removal |
| phase2_builder_implementation | 2026-03-21 | builder | Phase 2 complete: F/R coupling, persona views, dead code removal. 21/21 tests pass. |
| phase2_critic_code_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (1 med, 2 low). All 3 Phase 2 design FLAGs and all 4 Phase 1 code FLAGs verified fixed. R1 time_travel_revert() correct: uses to_stage from transition record, phase boundary guard with --force, F-label ⮌ format, R-label hints for cockpit. R2 persona-filtered dashboards correct: coordinate invariance preserved, PERSONA_STAGE_FILTERS with cross-phase visibility, format_dashboard_for_prompt() with max_lines cap, dispatch payload view_filter injection. FLAG-1 (MED): dual F-label generation (overlay un-numbered + engine numbered for same revert). FLAG-2 (LOW): filesystem revert doesn't prune completed stages dict. FLAG-3 (LOW): terminal _format_dashboard has no max_lines cap. Review at: pipeline_builds/orchestration-engine-v2-temporal_phase2_critic_code_review.md |
| phase2_critic_code_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (1 MED dual F-label paths, 2 LOW circular import + no test suite). All 3 design review FLAGs addressed. R1 F/R coupling correct. R2 persona views correct. Dead code removed. |
| phase2_critic_code_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (1 med, 2 low). All Phase 2 design + Phase 1 code FLAGs verified fixed. R1 time_travel_revert correct. R2 persona dashboards correct. Review at: pipeline_builds/orchestration-engine-v2-temporal_phase2_critic_code_review.md |
| phase2_complete | 2026-03-21 | architect | Phase 2 COMPLETE. Critic code review APPROVED 0 BLOCKs, 3 non-blocking FLAGs. All 3 Phase 2 design FLAGs and all 4 Phase 1 code FLAGs verified fixed. R1 time_travel_revert() correctly implemented: to_stage extraction, phase boundary guard with --force, F-label ⮌ format, R-label hints. R2 persona-filtered dashboards preserve coordinate invariance via additive filtering. FLAG-1 (MED): dual F-label paths (overlay un-numbered vs engine numbered) — recommend engine owns all F-labels in V3. FLAG-2 (LOW): filesystem stages dict not pruned on revert — temporal DB is authoritative, acceptable. FLAG-3 (LOW): terminal dashboard no max_lines — scrollable output, fine. Pipeline delivers: temporal overlay with SQLite+WAL, time-travel revert with causal F/R-label coupling, persona-scoped dashboards, dispatch payload view injection. Ready for deployment. |
| phase2_critic_code_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 3 FLAGs |

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
   ⮌ critic_design_review           2026-03-21   system                    Reverted from 
