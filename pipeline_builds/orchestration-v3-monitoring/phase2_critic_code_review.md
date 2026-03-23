# Orchestration V3 Monitoring — Phase 2 Critic Code Review

**Pipeline:** orchestration-v3-monitoring
**Phase:** 2 (Human-in-the-Loop)
**Date:** 2026-03-22
**Reviewer:** critic

---

## Verdict: ✅ APPROVED — 0 BLOCKs, 2 FLAGs (1 MED, 1 LOW)

Clean implementation. All 3 design-review FLAGs addressed correctly. All 4 Phase 1 FLAGs resolved. Script-pilot alignment maintained. Graceful degradation works throughout. ~310 lines of well-structured code across 7 files, matching the architect's design with appropriate builder discretion on implementation details.

---

## Criteria Assessment

### 1. Design Conformance ✅

The implementation faithfully follows the architect's design across all 7 modules:

| Module | Design Spec | Implementation | Match |
|--------|------------|----------------|-------|
| monitoring_views.py | RenderClient + .v5 + dual-source .v2 | ✅ All three implemented | Full |
| dependency_graph.py | Full compute_f_r_causal_chain | ✅ Structured parsing, R-label query, dep walk, orphan check | Full |
| codex_render.py | `refresh` + `subscribe` commands | ✅ Both in `_dispatch()` | Full |
| orchestration_engine.py | Refresh signal + view_context | ✅ Uses `refresh` not `anchor_reset`, trail embedded | Full |
| temporal_overlay.py | `get_transitions_since()` + heartbeat fix | ✅ Public API + `context_json` column | Full |
| temporal_schema.py | v2.1 migration | ✅ Idempotent ALTER TABLE | Full |
| wal_watcher.py | HTML escaping complete | ✅ All interpolated values escaped | Full |

### 2. Critic Design-Review FLAG Resolution ✅

**FLAG-1 (MED): Uses `refresh` not `anchor_reset` in _post_state_change** ✅

Verified at orchestration_engine.py line 196:
```python
_signal_render_engine('refresh', filepath=str(pipeline_md))
```
With comment explicitly noting the Critic FLAG-1 rationale. The `refresh` command in codex_render.py (line ~895) correctly calls `tree.apply_disk_change()` + `diff_engine.record()` + `notify_all()` — records the diff instead of wiping the buffer. Correct fix.

**FLAG-2 (LOW): HTML escaping complete** ✅

Verified at wal_watcher.py lines 233-236 — all stats values now wrapped in `html_escape(str(...))`. The builder correctly completed coverage over the only unescaped values (integer stats) while the existing user-facing strings (pipeline names, agent names) were already escaped.

**FLAG-3 (LOW): Structured diff parsing for causal chain** ✅

The builder chose option (b) from the design review — parsing the Δ/+/− text format in `RenderClient._parse_delta_text()` with a forward-compatible `get_diffs_structured()` that tries a structured endpoint first, falling back to text parsing. Pragmatic for Phase 2, clean upgrade path for later.

### 3. Phase 1 FLAG Resolution ✅

| Phase 1 FLAG | Resolution | Verified |
|-------------|-----------|----------|
| FLAG-1 (MED): heartbeat_extended session_id overwrite | `context_json` column via v2.1 migration in temporal_schema.py; heartbeat_extended writes to dedicated column | ✅ temporal_overlay.py:569 |
| FLAG-2 (LOW): render_live_diff private `_get_conn()` | Public `get_transitions_since()` method (temporal_overlay.py:577); render_live_diff calls it (monitoring_views.py) | ✅ No `_get_conn()` access from monitoring_views |
| FLAG-3 (LOW): HTML stats unescaped | `html_escape()` on all interpolated values in wal_watcher.py | ✅ Lines 233-236 |
| FLAG-4 (LOW): compute_f_r_causal_chain placeholder | Full implementation in dependency_graph.py (~75 lines): parse F-labels → query R-labels → walk deps → orphan check | ✅ |

### 4. Script-Pilot Alignment ✅

The implementation correctly maintains the script-pilot/agent-engine separation:

- **DispatchPayload.view_context** (orchestration_engine.py:391, :785): The *engine* calls `render_r_label_trail(pipeline=version, window_minutes=10)` and embeds the result. Agents receive a pre-rendered string, not query capabilities.
- **No UDS client code in agent sessions**: RenderClient is only used by monitoring_views.py and dependency_graph.py (script-side tooling), never in agent dispatch paths.
- **F-label origin remains the script**: `_post_state_change()` generates F-labels, triggers render engine refresh, and the R-labels flow from the render engine's diff processing. Agents observe, don't generate.

### 5. Graceful Degradation ✅

Every new capability has a fallback path when the render engine isn't running:

- **RenderClient.query()**: Returns `None` if socket doesn't exist (line: `if not self.SOCKET.exists(): return None`)
- **render_live_diff()**: Falls back to `overlay.get_transitions_since()` when no render_client
- **render_r_label_trail()**: Falls back to DB transitions rendered as F-label narrative when render engine unavailable
- **_post_state_change() refresh signal**: Wrapped in `try/except` with comment "Non-fatal — inotify is the primary mechanism"
- **compute_f_r_causal_chain()**: Generates predicted R-labels from F-label structure when RenderClient unavailable
- **v2.1 migration**: Idempotent column check before ALTER TABLE

### 6. Code Quality ✅

**Strengths:**
- Clean separation of concerns — each module has a clear responsibility
- Consistent error handling pattern: `try/except → fallback → pass` for non-fatal temporal operations
- Good docstrings with FLAG references and design decision callouts
- RenderClient is properly thin — single-shot socket, no persistent state, timeout-protected
- `_parse_delta_text()` handles all three diff types (Δ, +, −) with an `unknown` fallback

**No regressions detected:**
- v1-v4 renderers unchanged in signature and behavior
- VIEW_REGISTRY extended (key 5 added), not modified
- DispatchPayload gains `view_context` with empty string default — backward compatible
- All new imports are lazy (`from X import Y` inside functions) to avoid circular deps

---

## FLAGs

### FLAG-1 (MED): RenderClient socket read has no size bound

**Location:** monitoring_views.py, `RenderClient.query()` lines ~62-70

**Issue:** The read loop accumulates response data without a size limit:
```python
resp = b''
while b'\n' not in resp:
    chunk = s.recv(65536)
    if not chunk:
        break
    resp += chunk
```
If the render engine sends a very large response (e.g., a massive supermap or diff buffer), this could consume unbounded memory. The timeout protects against hanging, but not against a fast-delivered large payload.

**Risk:** Low in practice — render engine responses are typically <100KB. But as a UDS client that may be called in tight loops (e.g., multiple view renders), it's worth capping.

**Fix:** Add a max response size (e.g., 1MB):
```python
MAX_RESPONSE = 1 << 20  # 1MB
resp = b''
while b'\n' not in resp and len(resp) < MAX_RESPONSE:
    chunk = s.recv(65536)
    ...
```

### FLAG-2 (LOW): compute_f_r_causal_chain imports inside function body

**Location:** dependency_graph.py, `compute_f_r_causal_chain()` lines ~240, ~265

**Issue:** The function imports `monitoring_views.RenderClient` and `orchestration_engine.resolve_pipeline` inside the function body. While this avoids circular imports (correct motivation), the `ImportError` fallback for `resolve_pipeline` means affected versions can't be resolved from p-coordinates, silently producing an empty `affected_versions` set and therefore empty `cascading_deps`.

This isn't a bug — the function still returns valid (if incomplete) results. But the caller has no way to know the dep walk was skipped due to missing import vs. genuinely no affected versions.

**Fix (optional):** Add a `warnings` list to the return dict:
```python
result['warnings'] = ['resolve_pipeline unavailable — dep walk skipped']
```

---

## Summary

The builder delivered a clean Phase 2 implementation that:
1. Correctly addresses all 3 design-review FLAGs (refresh over anchor_reset, HTML escaping, structured diff parsing)
2. Resolves all 4 Phase 1 FLAGs
3. Maintains script-pilot alignment — agents receive pre-rendered views, never query independently
4. Degrades gracefully without the render engine
5. Introduces no regressions to existing functionality

FLAG-1 (MED) is a defensive hardening item, not a functional issue. FLAG-2 (LOW) is observability improvement.

**Recommendation:** Approve for merge. FLAG-1 can be addressed in a future hardening pass.
