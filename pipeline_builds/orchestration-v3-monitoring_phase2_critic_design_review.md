# Orchestration V3 Monitoring — Phase 2 Critic Design Review

**Pipeline:** orchestration-v3-monitoring
**Phase:** 2 (Human-in-the-Loop)
**Date:** 2026-03-22
**Reviewer:** critic

---

## Verdict: ✅ APPROVED — 0 BLOCKs, 3 FLAGs (1 MED, 2 LOW)

The design is architecturally sound, well-aligned with Shael's script-pilot directive, and implementable within the ~315 line budget. The render engine integration is correctly specified against the actual UDS protocol. All 4 Phase 1 FLAGs are addressed. The .v5 R-label trail is the right abstraction for script↔observer communication.

---

## Review by Criteria

### 1. Shael's Core Directive — Script-Led, Not Agent-Led ✅

**Verdict:** Fully aligned.

The design strengthens the script-pilot pattern in three concrete ways:
- **DispatchPayload.view_context** — the *script* decides what context the agent sees, not the agent. Agents receive a pre-rendered snapshot, not query capabilities. This is the right call (D5).
- **F→R label round-trip** — script writes state → disk change → inotify → render engine → R-label. The script's decisions are the *origin* of all R-labels. Agents observe, don't generate.
- **Stall detection via render diffs** — the script detects stalls using render engine data, not agent self-reporting. Script remains the authority.

The explicit render engine signal in `_post_state_change()` is a good latency optimization that doesn't compromise the inotify-primary design.

### 2. Render Engine Integration ✅

**Verdict:** Correctly specified against actual codex_render.py.

Verified against the codebase:
- ✅ `~/.belam_render.sock` — correct socket path (`SOCKET_PATH` in codex_render.py)
- ✅ `tree` command with `coord` and `prefix` params — exists in `_dispatch()` (line 869)
- ✅ `diff_since` command with `timestamp` param — exists (line 888)
- ✅ `supermap` command — exists (line 882)
- ✅ `anchor_reset` command — exists (line 892)
- ✅ `notify_all()` push to connected clients — exists in SessionManager
- ✅ JSON-line protocol (send JSON + `\n`, read JSON + `\n`) — matches `_signal_render_engine()` pattern

The two new commands (`refresh`, `subscribe`) are small additions to `_dispatch()`. `refresh` is essentially a wrapper around existing `apply_disk_change()` + `reindex_namespace()`. `subscribe` with pattern filtering is a nice-to-have but the design correctly marks it as optional optimization.

**RenderClient** design is sound — thin single-shot UDS client with `None` fallback. Matches the existing `_signal_render_engine()` pattern in codex_render.py (line 1447).

### 3. Phase 1 FLAG Resolution ✅

All 4 FLAGs addressed:

| FLAG | Fix | Assessment |
|------|-----|------------|
| FLAG-1: heartbeat_extended session_id overwrite | `context_json` column via v2.1 migration | ✅ Clean fix. `ALTER TABLE ADD COLUMN` is safe on SQLite. Idempotent check is correct. |
| FLAG-2: render_live_diff uses `overlay._get_conn()` | Public `get_transitions_since()` + RenderClient as primary | ✅ Proper encapsulation. Dual-source with render engine primary, DB fallback. |
| FLAG-3: HTML stats unescaped | `html_escape()` on all interpolated values | ✅ Simple, correct. See FLAG below about current code already using it. |
| FLAG-4: compute_f_r_causal_chain placeholder | Full implementation with render engine + dep graph | ✅ Good design: parse F-labels → query R-labels → walk dep graph → orphaned handoffs. |

### 4. Feasibility ✅

**Verdict:** Implementable within budget.

- ~315 lines across 7 existing files — no new files. This is proportionate.
- The sequencing (items 1-3 independent, 4-7 depend on 1-3) is correct and enables parallel work.
- The most complex piece is `compute_f_r_causal_chain` (~60 lines), which is well-scoped: parse, query, walk, return. No exotic algorithms.
- RenderClient (~40 lines) is straightforward socket I/O matching existing patterns.
- The v5 renderer (~30-40 lines) follows the established renderer pattern (v1-v4).

### 5. .v5 R-Label Trail ✅

**Verdict:** Correctly designed as the script-pilot → agent-observer communication channel.

The R-label trail is the render engine's diff stream rendered as temporal narrative. Key design decisions are sound:
- **D2 (separate from .v2):** Correct. .v2 is DB-backed state transitions; .v5 is render-engine-backed RAM diffs. Different sources, different granularity.
- **D4 (temporal correlation, not structural):** Correct. F→R correlation by timestamp proximity (~100ms window) avoids coupling the orchestration engine to DiffEntry internals.
- **Window parameter (default 30min):** Appropriate for R-label trail length management.

---

## FLAGs

### FLAG-1 (MED): `_signal_render_engine('anchor_reset')` semantics mismatch

**Location:** Section 3a — orchestration_engine.py render signal

**Issue:** The design calls `_signal_render_engine('anchor_reset')` as a "hint" for immediate pickup after `_post_state_change()`. But `anchor_reset` in the render engine (line 892) *resets the diff anchor*, which clears all accumulated diffs. This would wipe the diff buffer that .v5 reads from.

The design's intent is a **refresh hint** (re-scan disk now), not an anchor reset. The design even mentions adding a `refresh` command to codex_render.py (Section 6). The signal in `_post_state_change()` should use `refresh` (with the filepath of the changed pipeline .md), not `anchor_reset`.

**Fix:** Change the signal from `_signal_render_engine('anchor_reset')` to `_signal_render_engine('refresh', filepath=str(pipeline_md_path))`. This matches both the stated intent and the new `refresh` command the design already specifies.

### FLAG-2 (LOW): HTML escaping in wal_watcher.py — already partially applied

**Location:** Section 2b — FLAG-3 fix

**Issue:** The design shows the fix as wrapping stats values in `html_escape()`:
```python
{html_escape(str(stats.get('total_pipelines', 0)))} pipelines
```

Looking at the current wal_watcher.py, the stats line in the HTML template uses Python f-string interpolation (`{stats.get('total_pipelines', 0)}`). Since these are always integers from `get_dashboard()`, the actual risk is nil. But more importantly, the pipeline cards, agent badges, and dep rows already use `html_escape()` correctly (pipeline names, agent names, etc.). The stats are the only unescaped values. The fix is correct but the design should note that the *existing* code already applies `html_escape` to user-facing strings — the stats fix is completing coverage, not introducing a new pattern.

### FLAG-3 (LOW): `get_diff_since()` return type ambiguity

**Location:** Section 1a — RenderClient

**Issue:** `RenderClient.get_diff_since()` returns a `str` (the delta text), but the render engine's `diff_since` command (line 888-890) returns:
```python
{'ok': True, 'delta': self.diff_engine.get_delta_since(ts)}
```
where `get_delta_since()` returns a string in `Δ/+/−` format. This works for display in .v5, but the design also references using render diffs for the full `compute_f_r_causal_chain` implementation (Section 3c), which needs *structured* diff data (coord, field, old_value, new_value), not a rendered string.

**Fix:** Either: (a) add a `get_diffs_structured()` method to RenderClient that queries a new `diff_since_structured` command returning raw DiffEntry dicts, or (b) parse the `Δ/+/−` format back into structured data in `compute_f_r_causal_chain`. Option (a) is cleaner but adds scope; option (b) is pragmatic for Phase 2. Builder should decide.

---

## Design Strengths

1. **Graceful degradation is the right default.** Every new capability works with or without the render engine. This matches the existing system's resilience pattern.
2. **No new files.** All changes are enhancements to existing modules. This keeps the codebase footprint stable.
3. **DispatchPayload.view_context is elegant.** Pre-rendering the trail for the agent (D5) means agents stay pure executors. No UDS client code in agent sessions.
4. **The sequencing plan is correct.** Independent prerequisites (1-3) before dependent work (4-7). Builder can parallelize within each tier.
5. **D4 (temporal correlation)** avoids a fragile structural link between F-labels and R-labels. Timestamp proximity within ~100ms is reliable for single-machine orchestration.

---

## Summary

The design delivers on Shael's core directive: scripts remain the pilot, agents remain engines. The render engine integration is correctly specified against the actual UDS protocol. All Phase 1 FLAGs are addressed. The .v5 R-label trail is the right abstraction.

FLAG-1 (MED) is the only item that needs attention before build — using `anchor_reset` instead of `refresh` would break the diff buffer. FLAGs 2-3 are builder-discretion items.

**Recommendation:** Approve for build with FLAG-1 fix applied.
