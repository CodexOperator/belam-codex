# Orchestration V3: Real-Time Monitoring Suite — Critic Design Review

**Pipeline:** orchestration-v3-monitoring
**Stage:** critic_design_review
**Date:** 2026-03-21
**Reviewer:** critic
**Verdict:** ✅ APPROVED (0 BLOCKs, 5 FLAGs)

---

## 1. Review Summary

The architect's design for V3 monitoring is **well-structured, implementable, and correctly aligned with the task spec and Option C hybrid architecture**. The `.v` namespace design is clean and extensible, the three new modules have clear boundaries, and the WAL polling approach is pragmatically sound for our scale.

No blocking issues found. Five flags raised — two medium, three low — all addressable during build without design changes.

---

## 2. Checklist Verification

### 2.1 `.v` Namespace Design vs Task Spec ✅

| Task Spec Requirement | Design Coverage | Status |
|----------------------|----------------|--------|
| v1 turn-by-turn | `render_turn_by_turn()` in VIEW_REGISTRY[1] | ✅ |
| v2 live diff stream | `render_live_diff()` in VIEW_REGISTRY[2] | ✅ |
| v3 timeline | `render_timeline()` in VIEW_REGISTRY[3] | ✅ |
| v4 agent context | `render_agent_context()` in VIEW_REGISTRY[4] | ✅ |
| Suffix modifier pattern (`.v{M}`) | `parse_view_coord()` handles `e0p{N}.v{M}`, `e0v{M}`, `e0.v` | ✅ |
| Bare global forms (`e0v1`, `e0.v`) | Explicitly parsed | ✅ |
| Extensible registry | `VIEW_REGISTRY` dict + `view_config` table | ✅ |

**Assessment:** Full coverage. The coordinate grammar in §3.1 matches the task spec precisely. The dual representation (Python dict for runtime, `view_config` table for persistence/listing) is a nice touch.

### 2.2 Option C (Hybrid) Architecture ✅

| Component | Spec | Design |
|-----------|------|--------|
| Per-turn injection (agent-facing) | ✅ Required | ✅ §9.1 dispatch payload extension |
| Lightweight watcher (human-facing) | ✅ Required | ✅ §5 WAL watcher + canvas |
| Same SQLite DB, no duplication | ✅ Required | ✅ Both paths read `temporal.db` |
| Canvas rendering for Shael | ✅ Required | ✅ §5.3 HTML dashboard → canvas |
| SQLite WAL research | ✅ Required | ✅ §5.4 concludes WAL polling is sufficient |

**Assessment:** Architecture aligns perfectly with Option C as confirmed by Shael.

### 2.3 Three New Modules — Scope & Interfaces ✅

| Module | Responsibility | Coupling | LOC Est. |
|--------|---------------|----------|----------|
| `monitoring_views.py` | View resolution, rendering, VIEW_REGISTRY | Reads from temporal_overlay (data layer) | ~400 |
| `wal_watcher.py` | Change detection, HTML rendering, canvas push | Reads from monitoring_views (rendering), independent lifecycle | ~300 |
| `dependency_graph.py` | Dep CRUD, cascading resolution, graph rendering | Writes to temporal.db via overlay | ~250 |

**Assessment:** Clean separation of concerns. Each module has one job. Dependencies flow in one direction: `wal_watcher → monitoring_views → temporal_overlay ← dependency_graph`. No circular imports.

### 2.4 WAL Polling Approach ✅

**Soundness assessment:**
- `os.stat()` on WAL file at 2s intervals = negligible overhead ✅
- WAL checkpoint edge case (size reset) correctly identified and mitigated (monitor main DB mtime too) ✅
- Fallback for rollback mode (no WAL file) documented ✅
- No dependency on inotify/watchdog — portable, zero-dep ✅
- 2s latency acceptable for human-facing dashboard ✅

**Assessment:** Sound. The only exotic scenario is a WAL checkpoint occurring between two polls where the main DB mtime also doesn't change — but this would mean no data actually changed, so a missed poll is benign.

### 2.5 Cascading Dependency Resolution — Safety ✅ (with FLAG)

**Infinite loop risk:**
- Design mentions "tracks visited set to prevent cycles" in Risk Assessment table → ✅
- However, the `resolve_downstream_deps()` function signature and docstring (§8.2) don't mention the visited set parameter or cycle detection mechanism.

**Race condition risk:**
- Resolution is triggered by `_post_state_change()`, which runs synchronously in the completing agent's process. No concurrent resolution of the same pipeline. ✅
- Multiple pipelines completing simultaneously each trigger their own resolution — no shared mutable state. ✅
- `pipeline_dependency.status` updates are single-row UPDATEs with WHERE clause on specific (source, target) pairs — no risk of conflicting writes. ✅

**Assessment:** Safe, but cycle detection needs to be explicit in the function signature (see FLAG-1).

### 2.6 Builder Spec Implementability ✅

**Build order** (§13) is correct:
1. `temporal_schema.py` v2 migration — standalone, no deps ✅
2. `dependency_graph.py` — needs new tables from step 1 ✅
3. `monitoring_views.py` — needs dep graph for cross-pipeline views ✅
4. Engine + overlay integration — needs all three new modules ✅
5. `wal_watcher.py` — parallel with 3-4, standalone lifecycle ✅

**Critical path correctly identified.** Estimated ~950 lines new + ~80 modified is reasonable for the feature scope.

**All function signatures have clear types, docstrings, and return values.** Builder has enough information to implement without design ambiguity.

---

## 3. Flags

### FLAG-1 (MED): Cycle detection in `resolve_downstream_deps()` not specified in signature

**Location:** §4.6 Cascading Dependency Resolution, §8.2 function signatures

**Issue:** The risk table mentions "tracks visited set to prevent cycles" but the actual function signature doesn't include a `_visited: set = None` parameter or document the cycle detection algorithm. For a function that could theoretically recurse (if dep resolution triggers further completions), the mechanism needs to be explicit.

**Recommendation:** Add `_visited: set[str] | None = None` parameter to `resolve_downstream_deps()`. Initialize on first call, add `version` to visited before processing, skip any target already in visited. Log warning on cycle detection. This prevents infinite recursion if someone accidentally creates A→B→A deps.

**Severity:** Medium — without this, a circular dependency in the `pipeline_dependency` table could cause unbounded recursion. The function doesn't currently recurse (it resolves one level), but the `_post_state_change` hook could theoretically re-trigger if a dep resolution itself fires a state change. The design should be explicit about the depth bound.

### FLAG-2 (MED): `view_config` table vs `VIEW_REGISTRY` dict — dual source of truth

**Location:** §3.4 View Registry, §6.2 view_config table, §8.1 monitoring_views.py

**Issue:** Views are registered in two places: (1) Python `VIEW_REGISTRY` dict mapping int→function, (2) SQLite `view_config` table mapping int→metadata. These can drift. If someone adds a row to `view_config` without adding the Python renderer, `e0.v` will list a view that can't render. Conversely, if a renderer is added to `VIEW_REGISTRY` without a `view_config` row, the DB won't know about it.

**Recommendation:** Make `VIEW_REGISTRY` the single source of truth. Each entry should include metadata (name, description) alongside the renderer function. `list_views()` queries `VIEW_REGISTRY`, not the DB. The `view_config` table becomes optional persistence for external tooling (MCP in t4) rather than the authoritative registry. Alternatively, add a startup consistency check that validates VIEW_REGISTRY keys match view_config rows.

**Severity:** Medium — without reconciliation, `e0.v` could list phantom views or miss real ones. Easy to fix during build.

### FLAG-3 (LOW): `heartbeat_extended()` adds fields not consumed by any view renderer

**Location:** §4.2 Agent Activity Monitor

**Issue:** `heartbeat_extended()` adds `tokens_used` and `decisions_this_turn` to the context snapshot, but no view renderer in the design consumes these fields. The `.v4` renderer (`render_agent_context()`) uses `get_design_lineage()` and `get_agent_context()`, not heartbeat snapshots. The extended heartbeat data is write-only.

**Recommendation:** Either (a) document that these fields are for future use and skip implementing `heartbeat_extended()` in Phase 1, or (b) wire them into the `.v4` renderer. Option (a) is cleaner — build what's needed now, extend later.

**Severity:** Low — unnecessary code, not harmful.

### FLAG-4 (LOW): Schema version bump to 2 — verify_db() needs update

**Location:** §6.3 Schema Migration, temporal_schema.py lines 166-209

**Issue:** The current `verify_db()` checks for 6 required tables (`pipeline_state`, `state_transition`, `handoff`, `agent_context`, `agent_presence`, `schema_version`). V2 adds `pipeline_dependency` and `view_config`. The builder must update the `required` set in `verify_db()` to include the new tables, and add a migration path check (v1→v2 auto-migration when DB exists but is on v1).

**Recommendation:** Builder should:
1. Update `required` set in `verify_db()` to include new tables
2. Add `migrate_v1_to_v2()` function called by `init_db()` when existing DB has `schema_version = 1`
3. Make migration idempotent (CREATE IF NOT EXISTS already handles this)

**Severity:** Low — the design's `CREATE IF NOT EXISTS` makes migration safe regardless, but verification should match reality.

### FLAG-5 (LOW): `seed_dependencies_from_tasks()` — frontmatter `depends_on` uses task names, not pipeline versions

**Location:** §8.2 dependency_graph.py

**Issue:** Task frontmatter `depends_on` references task primitive names (e.g., `orchestration-engine-v2-temporal-autoclave`), but `pipeline_dependency` table uses pipeline version strings (e.g., `orchestration-engine-v2-temporal`). These don't always match — task names and pipeline version strings have diverged in practice. The seeding function needs a mapping layer.

**Recommendation:** `seed_dependencies_from_tasks()` should either: (a) maintain a task-name → pipeline-version mapping (fragile), or (b) seed only from pipeline markdown frontmatter `depends_on` which already uses pipeline version strings, or (c) skip auto-seeding and require explicit `register_dependency()` calls during pipeline creation (most reliable). Option (c) is cleanest — the launch-pipeline skill already knows both the task and the pipeline version.

**Severity:** Low — seeding is a convenience feature. Manual registration via `register_dependency()` works regardless.

---

## 4. Positive Observations

1. **Graceful degradation pattern preserved.** The dep resolution hook in `_post_state_change()` follows the exact same try/except/silent-failure pattern as existing temporal hooks. This is the right call — monitoring should never block orchestration.

2. **Backward compatibility is excellent.** No existing coordinate changes. `e0p3` without `.v` suffix falls through to existing orchestration behavior. Schema migration is purely additive. No existing tests should break.

3. **WAL research question resolved cleanly.** The task spec flagged this as needing research. The architect's analysis (§5.4) is pragmatic and correct — WAL file monitoring is sufficient for our scale, no exotic mechanisms needed.

4. **Build parallelism identified.** WAL watcher can be built in parallel with view renderers. Good for builder efficiency.

5. **Test checklist is comprehensive.** 25+ test cases covering coordinate parsing, rendering, dependency cascading, WAL edge cases, and integration. This gives the builder clear acceptance criteria.

6. **F/R causal chain design is thoughtful.** The `preview_revert()` dry-run wrapper is a clean addition that doesn't change the existing revert mechanism — it just adds visibility.

---

## 5. Verdict

**✅ APPROVED — 0 BLOCKs, 5 FLAGs (2 medium, 3 low)**

The design is sound, well-scoped, and implementable. The two medium flags (cycle detection explicitness and dual source of truth for view registry) should be addressed during build but don't require design changes. All three low flags are cleanup items.

Builder can proceed.
