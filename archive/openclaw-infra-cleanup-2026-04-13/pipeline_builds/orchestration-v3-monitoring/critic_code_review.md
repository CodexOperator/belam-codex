# Orchestration V3: Real-Time Monitoring Suite — Critic Code Review

**Pipeline:** orchestration-v3-monitoring
**Stage:** critic_code_review
**Date:** 2026-03-21
**Reviewer:** critic
**Verdict:** ✅ APPROVED (0 BLOCKs, 4 FLAGs — 1 medium, 3 low)

---

## 1. Review Summary

The builder delivered 3 new modules (`monitoring_views.py` 619L, `dependency_graph.py` 442L, `wal_watcher.py` 374L) and integrated them into 3 existing files (`orchestration_engine.py`, `temporal_overlay.py`, `temporal_schema.py`). All 5 design review FLAGs have been addressed. Code quality is high across all modules — clean separation of concerns, proper graceful degradation, robust error handling.

No blocking issues. Four flags raised — one medium, three low.

---

## 2. Design FLAG Verification

### FLAG-1 (MED): Cycle detection in `resolve_downstream_deps()` ✅ ADDRESSED

**Implementation:** `_visited: set = None` parameter added. Initialized on first call, version added to visited before processing, early return with stderr warning on cycle detection (dependency_graph.py L109-117).

**Assessment:** Correct. The function itself doesn't recurse — it resolves one level of deps. The `_visited` set is defense-in-depth for the theoretical case where `_post_state_change()` → `resolve_downstream_deps()` → state_transition INSERT somehow re-triggers the hook. In practice, the state_transition insert doesn't go through `_post_state_change()`, so the cycle path doesn't exist. But the guard is correct and harmless.

### FLAG-2 (MED): VIEW_REGISTRY authority ✅ ADDRESSED

**Implementation:** `VIEW_REGISTRY` dict with `ViewEntry` dataclass is the single source of truth. Each entry carries number, name, description, and renderer. `list_views()` reads from VIEW_REGISTRY, not the DB (monitoring_views.py L283-293). The `view_config` table is explicitly documented as "optional persistence for external tooling (MCP)" in both the module docstring and the migration SQL comment.

**Assessment:** Clean resolution. No dual-source-of-truth ambiguity.

### FLAG-3 (LOW): heartbeat_extended fields not consumed ✅ ADDRESSED

**Implementation:** `heartbeat_extended()` added to temporal_overlay.py (L543-578) with explicit docstring noting fields are "for future .v4 consumption" and "NOT consumed by .v4 renderer in Phase 1." The `.v4` renderer (`render_agent_context()`) uses `get_design_lineage()` as designed.

**Assessment:** Correctly deferred. No dead-write waste — the data IS stored (in agent_presence), just not rendered yet.

### FLAG-4 (LOW): verify_db() update ✅ ADDRESSED

**Implementation:** `required` set in `verify_db()` updated to include `pipeline_dependency` and `view_config` (temporal_schema.py L233). Auto-migration from v1→v2 in `init_db()` (L209-212). Migration is idempotent via `CREATE IF NOT EXISTS` + `INSERT OR IGNORE`.

**Assessment:** Complete. Schema version properly bumped to 2, migration path tested.

### FLAG-5 (LOW): Explicit dep registration ✅ ADDRESSED

**Implementation:** `seed_dependencies_from_tasks()` was dropped entirely. Dependencies are registered explicitly via `register_dependency()` (dependency_graph.py L53-82). No task-name-to-version scraping. CLI wired through both `dependency_graph.py register` and `orchestration_engine.py deps register`.

**Assessment:** Cleanest option (option C from the FLAG). Manual registration is reliable.

---

## 3. Coordinate Parsing Verification

### `parse_view_coord()` — monitoring_views.py L77-107

**Regex:** `r'^(?:e0)?(p\d+)?(?:\.v|v)(\d+)?$'`

| Input | Expected | Actual | Status |
|-------|----------|--------|--------|
| `e0p3.v2` | `('p3', 2)` | `('p3', 2)` via regex | ✅ |
| `e0v1` | `(None, 1)` | `(None, 1)` via regex | ✅ |
| `e0.v` | `(None, None)` | `(None, None)` via bare-forms check (L104) | ✅ |
| `e0p3` | `('p3', None)` | `('p3', None)` via `_PIPELINE_ONLY_RE` | ✅ |
| `p3.v2` | `('p3', 2)` | `('p3', 2)` via regex (e0 optional) | ✅ |
| `v1` | `(None, 1)` | `(None, 1)` via bare-forms check | ✅ |
| `garbage` | `(None, None)` | `(None, None)` fallthrough | ✅ |
| `e0v` | `(None, None)` | `(None, None)` via bare-forms check | ✅ |

**Edge case:** `p3.v` (pipeline + bare view) → regex matches with `(p3, None)`. `resolve_view()` treats `view_type=None` as "list views" regardless of pipeline_ref, so `p3.v` behaves identically to `.v`. This is correct behavior — view types are global, not pipeline-scoped.

---

## 4. Cascading Dependency Resolution — Safety Analysis

### No infinite loops ✅

`resolve_downstream_deps()` (dependency_graph.py L104-158):
1. `_visited` set initialized on first call
2. Version added to visited before processing (L114)
3. Early return if version already visited (L111-113)
4. Function resolves ONE level of downstream deps only — no recursive call
5. The `state_transition` INSERT at L141-148 is best-effort and doesn't trigger `_post_state_change()` (it's a direct DB insert, not going through the engine's state change machinery)

**Conclusion:** No recursion path exists. `_visited` is defense-in-depth.

### Connection safety ✅

All functions in dependency_graph.py use `try/finally: conn.close()` pattern. No connection leaks.

### Concurrency safety ✅

Resolution runs synchronously in the completing agent's process. `UPDATE ... WHERE id = ?` on specific dep rows — no conflicting writes possible. WAL mode handles concurrent readers.

### Trigger condition

`_post_state_change()` fires dep resolution when `to_stage in HUMAN_ACTIONS or action == 'archive'` (orchestration_engine.py L177). HUMAN_ACTIONS includes `pipeline_created` and `ready_for_colab_run` in addition to phase completion stages. This is slightly broader than the design's "phase completion or archive" trigger, but harmless — `resolve_downstream_deps()` only processes `status = 'pending'` deps, so extra calls with no matching deps are no-ops.

---

## 5. WAL Watcher Robustness Analysis

### Change detection (wal_watcher.py L63-84)

| Scenario | Handling | Status |
|----------|----------|--------|
| Normal write (WAL grows) | `st_size` change detected | ✅ |
| WAL checkpoint (size → 0) | Main DB `st_mtime` change caught | ✅ |
| No WAL file (rollback mode) | Monitors main DB mtime directly | ✅ |
| WAL file disappears mid-run | `OSError` caught, falls through to DB mtime check | ✅ |
| No changes | Returns False, no render | ✅ |
| Rapid consecutive changes | All detected (any size/mtime change triggers) | ✅ |

### Signal handling ✅

SIGTERM and SIGINT both caught (L198-200). `_running` flag checked between polls (L207). Graceful shutdown with render count report (L212).

### Error resilience ✅

`get_dashboard_data()` wrapped in try/except (L100). Canvas push failures logged to stderr (L184). Overlay properly closed (L110).

### Minor: first render is unconditional (L204)

`_do_render()` called before entering the poll loop — good. Ensures dashboard appears immediately on watcher start, not after first change.

---

## 6. Regression Analysis

### orchestration_engine.py

- New CLI commands (`view`, `deps`, `watcher`) added at L2938-3041 — **no existing commands modified**
- Dep resolution hook in `_post_state_change()` at L177-186 — wrapped in try/except with ImportError + general Exception catches. **Non-fatal, graceful degradation.** Existing behavior unchanged if dependency_graph.py is absent.
- Help text updated at L3058 to include new commands — informational only.

### temporal_overlay.py

- `heartbeat_extended()` at L543-578 — new method, no existing methods changed
- `render_view()` at L580-593 — new convenience method, no existing methods changed
- No signature changes to existing public methods

### temporal_schema.py

- `SCHEMA_VERSION` bumped 1→2 at L36
- `MIGRATION_V2_SQL` and `migrate_v1_to_v2()` added at L134-178
- `init_db()` modified to auto-migrate v1→v2 at L209-212 — uses `CREATE IF NOT EXISTS` + `INSERT OR IGNORE`, fully idempotent
- `verify_db()` required set expanded to include new tables at L233

**No regressions.** All changes are additive. Existing temporal functionality untouched.

---

## 7. Flags

### FLAG-1 (MED): `heartbeat_extended()` overwrites `session_id` with JSON blob

**Location:** temporal_overlay.py L567-575

**Issue:** When `context_snapshot` is provided, `heartbeat_extended()` stores the snapshot by overwriting the `session_id` column in `agent_presence` with a JSON dict `{"session": "...", "snapshot": {...}}`. This means consumers querying `agent_presence.session_id` expecting a plain string will get a JSON blob instead. The `_apply_presence_ttl()` and dashboard methods don't currently parse `session_id`, so no immediate breakage — but any future code reading `session_id` will need to handle both plain strings and JSON.

**Recommendation:** Either (a) add a `context_json` column to `agent_presence` via a v2.1 micro-migration, or (b) add a comment warning in `heartbeat_extended()` and `_apply_presence_ttl()` that `session_id` may contain JSON. Option (b) is fine for Phase 1.

**Severity:** Medium — no current breakage, but the column semantics are silently changed. A future developer could be surprised.

### FLAG-2 (LOW): `render_live_diff()` accesses `overlay._get_conn()` (private method)

**Location:** monitoring_views.py L166

**Issue:** `render_live_diff()` calls `overlay._get_conn()` to query `state_transition` directly. This breaks encapsulation — `_get_conn()` is prefixed with underscore indicating it's private. The builder did this because no public `get_transitions_since()` method exists on TemporalOverlay.

**Recommendation:** Either (a) add a `get_transitions_since(since, version=None)` public method to TemporalOverlay and use it, or (b) accept the coupling for Phase 1 and add a comment noting the encapsulation breach. Option (b) is pragmatic — the overlay and views are tightly coupled by design (same author, same module family).

**Severity:** Low — functional, just a coupling concern.

### FLAG-3 (LOW): HTML dashboard missing XSS protection for notes field

**Location:** wal_watcher.py L172 (`render_html_dashboard`)

**Issue:** Pipeline version, stage, and agent fields are properly escaped via `html_escape()`. However, the `stats` dict values at L152 are rendered directly into HTML without escaping. While these are integer values from the overlay and pose no real XSS risk (they're controlled data), the inconsistency is worth noting.

**Severity:** Low — controlled data source, no real attack vector. Internal dashboard only.

### FLAG-4 (LOW): `compute_f_r_causal_chain()` is a stub

**Location:** dependency_graph.py L238-270

**Issue:** The function does basic string matching on `.stage` and `.agent` in F-labels. The architect's design showed richer causal analysis including handoff invalidation and session orphaning. The current implementation returns surface-level R-labels only.

**Recommendation:** Document as Phase 1 placeholder. The function signature and return format are correct — richer analysis can be added incrementally without API changes.

**Severity:** Low — functional for basic use, richer analysis is a Phase 2 concern.

---

## 8. Positive Observations

1. **All 5 FLAGs addressed cleanly.** No shortcuts taken — each FLAG has a clear implementation with explicit docstring references to the FLAG number and resolution approach.

2. **Module boundaries are clean.** monitoring_views.py imports from temporal_overlay (data), dependency_graph.py is independent (own connections), wal_watcher.py imports from both (rendering). No circular imports.

3. **Graceful degradation throughout.** Every cross-module import is wrapped in try/ImportError. The system works in degraded mode if any module is missing. This matches the established V2 pattern perfectly.

4. **CLI is comprehensive.** All three modules have standalone CLI entry points. The engine's `view`, `deps`, and `watcher` commands provide unified access. Both `--json` mode and human-readable output are supported.

5. **ViewEntry dataclass is elegant.** Carrying metadata alongside the renderer in the registry eliminates the dual-source-of-truth problem completely.

6. **WAL watcher is production-ready.** Signal handling, error recovery, canvas + terminal modes, single-render mode, configurable interval. Well-engineered for a lightweight monitoring tool.

7. **Schema migration is bulletproof.** CREATE IF NOT EXISTS + INSERT OR IGNORE + auto-migration in init_db(). Can't break existing DBs.

---

## 9. Code Quality Summary

| Module | Lines | Quality | Notes |
|--------|-------|---------|-------|
| monitoring_views.py | 619 | ⭐⭐⭐⭐ | Clean renderers, proper typing, good CLI |
| dependency_graph.py | 442 | ⭐⭐⭐⭐ | Solid CRUD, safe resolution, good CLI |
| wal_watcher.py | 374 | ⭐⭐⭐⭐⭐ | Production-quality polling, HTML, canvas |
| orchestration_engine.py changes | ~100 | ⭐⭐⭐⭐ | Non-invasive integration, proper error handling |
| temporal_overlay.py changes | ~55 | ⭐⭐⭐⭐ | Clean delegation, FLAG-3 properly deferred |
| temporal_schema.py changes | ~80 | ⭐⭐⭐⭐⭐ | Idempotent migration, verify_db updated |

---

## 10. Verdict

**✅ APPROVED — 0 BLOCKs, 4 FLAGs (1 medium, 3 low)**

All 5 design review FLAGs addressed. Coordinate parsing handles all forms correctly. Cascading dependency resolution is safe (no infinite loops, proper visited set, single-level resolution). WAL watcher is robust across all edge cases. No regressions to existing functionality. Code quality is consistently high.

Builder can proceed to phase completion.
