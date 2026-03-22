# Codex Engine V3: Critic Design Review

**Pipeline:** codex-engine-v3  
**Stage:** critic_design_review  
**Agent:** critic  
**Date:** 2026-03-22  
**Verdict:** ✅ APPROVED — 0 BLOCKs, 5 FLAGs (2 MED, 3 LOW)

---

## Review Summary

The design is well-structured. Four modules cleanly wrap V2 without bloating it (~80 lines added to codex_engine.py, rest in new files). Separation of concerns is correct: MCP server, mode-switch, materialization, and multi-pane rendering are independent modules that compose through existing engine APIs. No scope creep — all four capabilities map directly to the task spec's acceptance criteria.

### Checklist

| Criterion | Verdict | Notes |
|-----------|---------|-------|
| MCP server design (stdio JSON-RPC, codex:// URIs, resource/tool split) | ✅ PASS | Clean architecture. `register_codec()` API confirmed at codex_codec.py:241. Correct use of `application/x-codex` content type. |
| Live mode-switch (e0x) well-scoped and non-destructive | ✅ PASS | View transformation only — primitives untouched. Sort mode registry is clean. See FLAG-1 and FLAG-3. |
| Reactive materialization subsumes --boot | ✅ PASS | `--boot` delegates to `CodexMaterializer.boot()`. Hash-based diffing avoids redundant work. Existing `BEGIN:SUPERMAP`/`END:SUPERMAP` markers reused. |
| Multi-pane rendering practical | ✅ PASS | `watch -n2` + tmux is simple and pragmatic. `--render` works standalone without tmux. No new dependencies. |
| Builder spec implementable | ✅ PASS | Build order correct (engine mods → materializer → panes → MCP). Test checklist comprehensive (32 items). Line estimates realistic. |
| No over-engineering or scope creep | ✅ PASS | Deferred items (vector-direct encoding, mobile viewport, MCP subscriptions, multi-workspace) correctly excluded. |

---

## Detailed Findings

### 1. MCP Server — Sound

- **URI scheme:** `codex://workspace/<coord>` is correct per MCP spec (custom schemes, not `mcp://`). Namespace-only URIs (`codex://workspace/m`) vs specific-primitive URIs (`codex://workspace/m152`) are distinguishable by the presence of digits — matches existing `resolve_coords()` behavior.
- **R-label diffs across reads:** Clever reuse of `RenderTracker` per MCP session. The per-session tracker instance is the right call — different clients see their own diff state.
- **Tool surface:** 5 tools exposed (navigate, edit, create, graph, supermap). Minimal and correct — maps to the V2 operation set without exposing internals.
- **No new dependencies:** stdio JSON-RPC is just `json.loads(stdin)` / `json.dumps(stdout)`. Verified: no websocket or HTTP server needed.

### 2. Live Mode-Switch — Clean, Two Issues

- **Sort mode registry:** `SORT_MODES` dict with lambda sort keys is elegant. `shuffle` as a special case (post-sort `random.shuffle`) makes sense.
- **`--shuffle` as one-shot flag:** Correctly distinguished from persistent `e0x shuffle`. Same convention as `--as`, `--depth`.
- **F-label tracking:** Mode-switch recorded as `F23 Δ engine.sort_mode alpha→shuffle`. R-label shows coordinate reassignments. Good observability.
- See FLAG-1 (insertion point) and FLAG-3 (persistence gap).

### 3. Reactive Materialization — Correct Subsumption

- **`--boot` delegation:** The proposed change to `main()` is minimal — 4 lines replacing the existing inline implementation. Verified current `--boot` at codex_engine.py:4111-4135.
- **Hash-based diffing:** `state/materialize_hashes.json` stores per-coordinate hashes. Only changed primitives generate diff entries. Correct for workspace of ~100 primitives.
- **Multi-doc `.codex` stream:** Supermap + diff in a single file, `---` separated. Clean format compatible with `codex_codec.py`'s existing stream parsing (`iter_codex_stream` confirmed at codec level).
- **No daemon:** Correct decision. Materialization on boot + post-mutation is simpler and more predictable than filesystem watching.

### 4. Multi-Pane Rendering — Practical

- **Three renderers:** Dense reuses `render_supermap()`/`render_zoom()`. JSON reuses `load_primitive()` + `json.dumps()`. Pretty is the only new renderer. Minimal new code.
- **tmux dependency:** Only `--start` requires tmux. All `--render` modes work standalone. Graceful degradation confirmed.
- **`watch -n2` refresh:** Simple polling — no inotify complexity. 2-second refresh is appropriate for a debugging/teaching tool.
- **Monitoring view integration:** `codex_panes.py --start e0p3.v1` for monitoring views is a nice touch but should be a stretch goal, not builder-blocking.

---

## FLAGS

### FLAG-1 (MED): `e0x` insertion point in `_parse_e0_args()` not specified

The design shows the detection logic:
```python
if first_arg.startswith('x'):
    spec['op'] = 'mode_switch'
```

But doesn't specify WHERE in `_parse_e0_args()` this goes relative to the existing branching. The current function (codex_engine.py:3632-3730) has this order:

1. Check `SINGLE_OPS` dict (`g`, `h`, `s`, `k`, `l`, `r`)
2. Check pipeline coordinate (`p\d+`)
3. Check named operations (`dispatch`, `handoff`, `unlock`, `sweep`, etc.)
4. Fallback to `legacy`

`'x'` isn't in `SINGLE_OPS`, so it would fall through to step 2 (pipeline check fails), then step 3. The builder needs to either:
- **(a)** Add `'x': 'mode_switch'` to `SINGLE_OPS` (simplest — then `e0x` matches like `e0g`), OR
- **(b)** Add explicit `startswith('x')` check between steps 1 and 2.

**Recommendation:** Option (a) — add to `SINGLE_OPS`. This preserves the existing dispatch pattern and makes `e0x` work identically to `e0g`/`e0h`/`e0s`. The sub-argument parsing (`shuffle`, `alpha`, `priority`, etc.) happens inside `_dispatch_e0` when `spec['op'] == 'mode_switch'`, using `spec['extra']`.

### FLAG-2 (LOW): Async method signatures vs sync stdio transport

The design declares MCP server methods as `async def handle_resources_list(self)`. For a stdio transport (blocking `stdin.readline()` → `json.loads()` → dispatch → `json.dumps()` → `stdout.write()`), async isn't necessary and adds complexity. The builder should either:
- Use sync methods with a simple `while True: line = stdin.readline()` loop, OR
- Use `asyncio.run()` in main with `asyncio.StreamReader` for stdin if they want async (e.g., for future SSE/subscription support).

**Recommendation:** Start sync. The MCP spec's stdio transport is inherently synchronous. Async can be added when subscriptions land (deferred per Non-Goals).

### FLAG-3 (MED): Sort mode doesn't persist across CLI invocations

Since each `python3 codex_engine.py e0x shuffle` is a new process, `_current_sort_mode` resets to `'alpha'` on every invocation. The design acknowledges this ("session-scoped, resets on CLI restart") and notes the materializer records sort mode in `state/materialize_hashes.json`.

**The gap:** There's no mechanism for `codex_engine.py` to READ the persisted sort mode on startup. If an agent runs `e0x priority` then later runs `e0 p3` (no mode arg), they get alpha-sorted output — the mode switch was lost.

**Fix:** Add a small init block in `main()` or `get_primitives()` that reads `sort_mode` from `state/materialize_hashes.json` if it exists:

```python
def _load_persisted_sort_mode():
    global _current_sort_mode
    hash_file = WORKSPACE / 'state' / 'materialize_hashes.json'
    if hash_file.exists():
        data = json.loads(hash_file.read_text())
        if 'sort_mode' in data:
            _current_sort_mode = data['sort_mode']
```

And `set_sort_mode()` should persist the change:
```python
def set_sort_mode(mode: str) -> str:
    ...
    _persist_sort_mode(_current_sort_mode)  # write to hash file
```

### FLAG-4 (LOW): Sort key reads frontmatter for every primitive on every sort

`_apply_sort_mode()` calls `parse_frontmatter(fp.read_text(...))` inside the sort key lambda for `priority` and `recent` modes. For ~100 primitives this is fine, but it's file I/O in a sort comparator — called O(n log n) times.

**Recommendation:** Pre-read frontmatter once, build a sort key dict, then sort. The design's `_priority_sort_key(fm)` signature implies fm is passed in, but the wrapper lambda does the read. Builder should batch-read first.

### FLAG-5 (LOW): `materialize_affected()` integration points unspecified

The design says `materialize_affected(coord)` is "called after F-label mutations in `execute_edit()`, `execute_create()`" but doesn't show the exact insertion points. Since each CLI invocation is a new process, this must be called WITHIN the same process that performed the mutation.

**Recommendation:** Builder should add `materialize_affected()` calls at the end of `execute_edit()` (after file write, codex_engine.py:~1870) and `execute_create()` (after file write, codex_engine.py:~2100). Keep it as `try/except` to avoid mutation failure if materialization breaks.

---

## Verification Against Task Spec

| Task Spec Requirement | Design Coverage | Status |
|----------------------|-----------------|--------|
| MCP server returns resources in codex engine format | §1 MCP-Native Codex Server | ✅ |
| `mcp://belam/codex/t1` → primitive | `codex://workspace/t1` (corrected URI scheme) | ✅ |
| R-label diffs as usage docs | R-label diff header in MCP responses | ✅ |
| codex_codec.py handles boundary translation | Codec used via `to_codex()`/`from_codex()` | ✅ |
| External MCP clients get codex-native representations | stdio transport + `application/x-codex` | ✅ |
| Live-swap coordinate grammar mid-session | `e0x` + SORT_MODES registry | ✅ |
| Forces supermap re-render in new format | Auto-render after mode-switch | ✅ |
| `--shuffle` as view modifier flag | One-shot `--shuffle` flag | ✅ |
| `.codex` files as materialized views | `CodexMaterializer` + `CODEX.codex` | ✅ |
| `before_prompt_build` reads fresh `.codex` | Boot-time materialization via `--boot` | ✅ |
| Agent sees temporal diff | Diff section in multi-doc `.codex` stream | ✅ |
| No daemon | Explicit trigger points (boot, post-mutation, on-demand) | ✅ |
| Tmux split: 3 panes | `codex_panes.py --start` with dense/json/pretty | ✅ |
| Auto-parser renders same workflow in all three | `watch -n2` polling same state | ✅ |

**All acceptance criteria covered. No gaps.**

---

## Conclusion

The design is clean, well-scoped, and implementable. The four modules correctly separate concerns and compose through existing V2 APIs without modifying core behavior. The ~80 lines added to `codex_engine.py` (sort mode + e0x dispatch) are surgical.

**FLAGs summary:**
- FLAG-1 (MED): Add `'x': 'mode_switch'` to `SINGLE_OPS` for clean dispatch
- FLAG-2 (LOW): Use sync methods for MCP server, not async
- FLAG-3 (MED): Add sort mode persistence read/write across CLI invocations
- FLAG-4 (LOW): Batch frontmatter reads in sort key, don't read per-comparison
- FLAG-5 (LOW): Specify exact `materialize_affected()` insertion points in execute_edit/create

None are blockers. Builder can address all five during implementation.

**APPROVED for build.**
