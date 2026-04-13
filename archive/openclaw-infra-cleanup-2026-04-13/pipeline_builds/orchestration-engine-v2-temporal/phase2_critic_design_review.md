# Orchestration Engine V2-Temporal — Phase 2 Critic Design Review

**Pipeline:** orchestration-engine-v2-temporal
**Author:** Critic (Belam) 🔍
**Date:** 2026-03-21
**Reviewed:** `orchestration-engine-v2-temporal_phase2_architect_design.md`
**Ground truth:** `orchestration-engine-v2-temporal_phase2_direction.md` (Shael)
**Verdict:** ✅ APPROVED — 0 BLOCKs, 3 FLAGs (1 medium, 2 low)

---

## 1. Direction Alignment Check

### R1: F-label/R-label Time Travel — Causal Coupling

**Shael's requirement:** "F-label undo → filesystem revert → triggers R-label re-render of affected supermap sections. The two label systems should be causally linked, not independent."

**Design response:** `time_travel_revert()` applies filesystem changes (F-label domain) and returns `RevertResult` containing `r_label_hint` — a dict telling the cockpit what supermap sections need re-rendering. Coupling is informational (engine provides hints, cockpit owns the render).

**Verdict: ✅ ALIGNED.** The causal chain is clear: revert → F-labels generated → r_label_hint emitted → cockpit re-renders. The ⮌ format for revert F-labels is a good design choice — parseable and visually distinct from forward Δ mutations. The boundary preservation (engine owns F-labels, cockpit owns R-labels) is correct and matches the existing engine header contract.

**One nuance worth noting:** The design correctly scopes revert to *state-level* (which pipeline stage), not *content-level* (file contents). This matches Shael's example use case ("undo back to F1") and avoids the complexity of git-based content revert. Content revert deferred to V3 is the right call.

### R2: Persona-Filtered Dashboard Views

**Shael's requirement:**
- Global coordinates always valid (never remapped)
- Dashboard filtered view per persona binding
- `--as architect` or `i1` filters to architect-relevant state
- Orchestration sets the view filter when dispatching — agents don't choose
- View filter is metadata in dispatch payload, not coordinate transformation

**Design response:**
- D4 explicitly states "Global coordinates are never remapped"
- `PERSONA_STAGE_FILTERS` defines per-persona visibility
- `get_dashboard(persona=)` filters rows, not coordinates
- `build_dispatch_payload()` sets the filter based on agent being dispatched
- `view_filter` added to `DispatchPayload` as metadata

**Verdict: ✅ ALIGNED.** All five of Shael's sub-requirements are addressed. The filtering-as-additive-hiding principle (D4) is exactly what was asked for. The dispatch-side control (D5) prevents agents from choosing their own view.

### FLAG-1: Dead Code Removal

**Shael's requirement:** Remove `record_transition()` dead code with broken atomicity claim.

**Design response:** Delete lines 233-267 of temporal_overlay.py. Zero callers verified.

**Verdict: ✅ ALIGNED.** I independently verified: `grep -rn "record_transition" scripts/ --include="*.py"` returns only the definition itself and the docstring/comment block. Zero call sites in orchestration_engine.py, temporal_sync.py, or anywhere else. Safe to delete.

### FLAGs 2-4: Fix If Touched

**Shael's requirement:** "Fix if touched, don't prioritize."

**Design response:** FLAG-2 will be fixed because `_format_dashboard()` is touched for R2. FLAG-3 fixed proactively (5 lines). FLAG-4 deferred (resolves naturally).

**Verdict: ✅ ALIGNED.** Reasonable scoping. FLAG-3 proactive fix is a good call at 5 lines.

### V3 Deferrals

**Shael's requirement:** Real-time monitoring, live dashboard — design as v3/monitoring suite.

**Design response:** Section 5.5 Non-Goals explicitly lists these as out of scope.

**Verdict: ✅ NO SCOPE CREEP.** The design stays within Shael's Phase 2 boundary.

---

## 2. Design Quality Review

### 2.1 R1 — `time_travel_revert()` Implementation

**Strengths:**
- Clean five-step flow: query target → compute diff → apply filesystem → log transition → return result
- `RevertResult` structure is well-defined with all needed fields
- Graceful degradation preserved (returns None on failure)
- Read-only `time_travel()` is untouched — revert is additive

**FLAG-1 (MED): `time_travel()` returns a single transition row, not reconstructed state.**

The existing `time_travel()` method (temporal_overlay.py:612-632) queries `state_transition` for the latest row at-or-before the timestamp. It returns a *transition record* (`{from_stage, to_stage, agent, action, ...}`), not a *pipeline state snapshot*. The design says step 1 calls `time_travel()` to "get target state" and step 2 reads "current state from `pipeline_state` table" — but the target state needs to be *derived* from the transition's `to_stage` field, not read directly. 

The builder spec (step 3) says "Call `time_travel(version, target_timestamp)` to get target state" — this is slightly misleading. The builder should understand that `time_travel()` returns a transition, and the *target state* is `transition['to_stage']` (the stage the pipeline was in *after* that transition).

**Impact:** Medium — if the builder treats the transition row as a full state object, the diff computation in step 2 will fail or produce wrong results. The function signature section (5.2) has the right idea in the docstring but the implementation steps (5.3, step 3) should clarify the mapping.

**Recommendation:** Builder spec step 3 should note: "Extract target stage from `transition['to_stage']`. The transition row is NOT a pipeline_state row — derive needed fields."

### 2.2 R2 — Persona Filtering

**Strengths:**
- `PERSONA_STAGE_FILTERS` is well-structured and complete
- Architect gets visibility into critic output (good — needs review results)
- Filtering is view-level, coordinates untouched
- Dispatch injection is clean — filtered dashboard appended to task prompt

**FLAG-2 (LOW): `show_stages` lists are incomplete for cross-phase visibility.**

The architect's `show_stages` includes `phase2_architect_design` and `phase2_architect_revision` but not `phase2_builder_implementation` — yet the architect needs to see builder output when reviewing Phase 2 completeness. Similarly, the critic's list lacks `builder_implementation` — the critic reviews builder output and should see the build stage to know what's pending review.

**Impact:** Low — filtering is *de-emphasis*, not hard hiding. Non-listed stages are still visible but de-emphasized (Section 2.6: "Non-active pipelines are still visible but de-emphasized"). So this is a cosmetic issue, not a functional one.

**Recommendation:** Consider adding cross-stage visibility entries, or document that de-emphasis (not hiding) makes this safe.

### 2.3 FLAG-1 Deletion

**Verified correct.** `record_transition()` at lines 233-267:
- Uses `BEGIN IMMEDIATE` but sub-methods each `conn.commit()` internally → broken atomicity
- Zero callers in codebase (confirmed by grep)
- The separated pattern (`log_transition` + `advance_pipeline` + `create_handoff` called individually from `_post_state_change`) is the intended design
- Clean deletion, no downstream breakage

### 2.4 Design Decisions

All five decisions (D1-D5) are sound and well-justified. D3 (coupling via hints, not direct emission) is particularly good — it achieves Shael's causal coupling requirement while preserving the F/R ownership boundary.

---

## 3. Builder Spec Implementability

### 3.1 Function Signatures ✅
All new method signatures are clear, typed, and have docstrings explaining behavior. Return types are specified.

### 3.2 Implementation Steps ✅
10 steps, logically ordered (FLAG-1 deletion first → R1 features → R2 features → cosmetic fixes). Dependencies flow correctly.

### 3.3 Test Checklist ✅
17 tests covering: core functionality (T1-T7), filtering (T8-T13), deletion (T14), cosmetics (T15), CLI (T16), invariant (T17). Good coverage.

**FLAG-3 (LOW): No test for revert-of-revert behavior.**

Open Question 2 asks about revert chain handling. The answer ("always reverts to specified timestamp") is correct but there's no test case for it. A second revert to a different timestamp after a first revert should work correctly — the temporal DB will have the revert transition logged, and querying at a pre-revert timestamp should return the original state.

**Impact:** Low — the behavior is deterministic by design (timestamp-based query), but an explicit test prevents future regression if revert logging changes.

**Recommendation:** Add T18: "Second `time_travel_revert()` to a different timestamp after a prior revert succeeds and produces correct state."

---

## 4. Open Questions — Critic Answers

**Q1: Revert scope guard (cross-phase)?**
**Answer:** Yes, add a guard. Phase boundaries are significant lifecycle events. A revert from Phase 2 back into Phase 1 would invalidate Phase 1 completion and all Phase 2 work. The guard should be a warning + `--force` flag, not a hard block. Log the override if forced.

**Q2: Revert chain handling?**
**Answer:** Current design (always revert to specified timestamp) is correct. Reverts are entries in the transition log, not a separate undo stack. Any timestamp query naturally handles prior reverts.

**Q3: Dashboard injection size?**
**Answer:** Cap at 80 lines or 4000 characters. Dispatch payloads are task prompts consumed by LLMs — large injections waste context tokens. Add a `max_lines` parameter to `format_dashboard_for_prompt()` with a sensible default.

**Q4: FLAG-3 proactive fix?**
**Answer:** Fix proactively. 5 lines, improves dashboard accuracy, low risk.

---

## 5. Summary

| Item | Verdict | Notes |
|------|---------|-------|
| R1: F/R causal coupling | ✅ Aligned | Clean chain, boundary preserved |
| R2: Persona-filtered views | ✅ Aligned | All 5 sub-requirements met |
| FLAG-1 removal | ✅ Correct | Zero callers, safe delete |
| FLAGs 2-4 scoping | ✅ Reasonable | Fix-if-touched + proactive FLAG-3 |
| No scope creep | ✅ Clean | V3 items explicitly deferred |
| Builder spec | ✅ Implementable | Clear steps, signatures, tests |

### FLAGs

| # | Severity | Issue | Recommendation |
|---|----------|-------|----------------|
| FLAG-1 | MED | `time_travel()` returns transition row, not state snapshot — builder spec step 3 should clarify field derivation | Add note: extract `to_stage` from transition; don't treat as pipeline_state row |
| FLAG-2 | LOW | `show_stages` slightly incomplete for cross-phase visibility (e.g., architect can't see builder stage) | Document that de-emphasis (not hiding) makes this safe, or add entries |
| FLAG-3 | LOW | No test for revert-of-revert behavior | Add T18: second revert to different timestamp after prior revert |

**Overall: APPROVED.** Design is faithful to Shael's direction, well-scoped, and implementable. The one medium FLAG is a builder-guidance clarification, not a design flaw.

---

*Critic review complete. Ready for builder implementation.*
