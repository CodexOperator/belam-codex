# Codex Engine V3: Critic Code Review

**Pipeline:** codex-engine-v3  
**Stage:** critic_code_review  
**Agent:** critic  
**Date:** 2026-03-22  
**Verdict:** ✅ APPROVED — 0 BLOCKs, 3 FLAGs (1 MED, 2 LOW)

---

## Review Summary

All 3 new modules (`codex_mcp_server.py` 486L, `codex_materialize.py` 351L, `codex_panes.py` 333L) and engine modifications (+179L in `codex_engine.py`) are well-implemented. The builder addressed all 5 design-review FLAGs. Code is clean, modular, and introduces no regressions to existing engine functionality. Each module imports from the engine without modifying core APIs — exactly as designed.

---

## Design FLAG Resolution

| FLAG | Severity | Status | How Addressed |
|------|----------|--------|---------------|
| FLAG-1: `e0x` insertion point / SINGLE_OPS dispatch | MED | ✅ RESOLVED | `'x': 'mode_switch'` added to `SINGLE_OPS` dict (engine:3798). Clean dispatch alongside `e0g`, `e0h`, `e0s`. |
| FLAG-2: Sync MCP (not async) | LOW | ✅ RESOLVED | All server methods are sync (`def`, not `async def`). `main()` uses blocking `while True: readline()` loop. No asyncio overhead. |
| FLAG-3: Sort mode persistence across invocations | MED | ✅ RESOLVED | `_load_persisted_sort_mode()` reads from `state/materialize_hashes.json` on module import (engine:190). `_persist_sort_mode()` writes on every `set_sort_mode()` call (engine:150). |
| FLAG-4: Batch frontmatter reads in sort | LOW | ✅ RESOLVED | `_apply_sort_mode()` reads frontmatter once into `enriched` list, then sorts (engine:170-180). No per-comparison I/O. |
| FLAG-5: `materialize_affected()` insertion points | LOW | ✅ RESOLVED | Called at end of `execute_edit()` (engine:2114) and `execute_create()` (engine:2272). Both wrapped in `try/except` — materialization failures cannot break mutations. |

---

## Module Reviews

### 1. `codex_mcp_server.py` (486 lines) — PASS

**JSON-RPC implementation:** Correct. `read_jsonrpc()` supports both Content-Length framing and line-delimited JSON (handles varied MCP clients). `write_jsonrpc()` uses Content-Length framing consistently. Error codes follow JSON-RPC 2.0 spec (-32601 method not found, -32602 invalid params, -32603 internal error).

**MCP protocol:** `initialize` returns correct capability structure with `protocolVersion`. `initialized` notification returns `None` (no response — correct for notifications). `ping` handled. Resource and tool methods properly separated.

**Resource URIs:** `codex://workspace/<coord>` correctly parsed via regex. `_parse_uri()` is clean. Supermap and memory exposed as special resources. `mimeType: application/x-codex` used for primitives, `text/plain` for aggregates.

**Tool surface:** 5 tools matching design spec. `codex_edit` and `codex_create` correctly capture stdout via `io.StringIO` redirect and restore. `isError` flag set on non-zero return codes.

**RenderTracker integration:** Per-session `RenderTracker` instance with dedicated state file (`mcp_render_state.json`) — isolates MCP tracking from CLI tracking. Correct.

**Lazy imports:** `_get_engine()` / `_get_codec()` avoid import-time side effects. `sys.path.insert(0, ...)` is the standard pattern used across all engine modules.

**Robustness:** Main loop catches exceptions without crashing, logs to `state/mcp_server.log`. EOF detection (`message is None → break`) handles clean client disconnect.

### 2. `codex_materialize.py` (351 lines) — PASS

**Hash-based diffing:** SHA-256 truncated to 12 chars per primitive. Hashes stored in `state/materialize_hashes.json` per coordinate. Change detection correctly identifies added (+), modified (Δ), and removed (-) primitives. First-run case handled (skips diff when `old_prim_hashes` is empty).

**Supermap hash:** `_hash_content()` strips volatile timestamps before hashing — prevents false diffs from timestamp changes alone. Good detail.

**Boot flow:** `boot()` → `materialize_full()` → `_read_supermap_from_codex()` → `inject_into_agents_md()`. Correctly reuses existing `BEGIN:SUPERMAP`/`END:SUPERMAP` markers. Fallback to `render_supermap()` if CODEX.codex parsing fails.

**Incremental materialization (`materialize_affected`):** Correctly designed as lightweight — only updates hash state, defers full re-render to next boot. Coordinate resolution via regex parsing is correct and handles multi-char prefixes (`md`, `mw`).

**Multi-doc `.codex` stream:** Supermap + diff sections separated by `---`. Format matches design spec.

**CLI interface:** `--boot`, `--full`, `--diff` modes via argparse. `--workspace` override available. Clean.

### 3. `codex_panes.py` (333 lines) — PASS

**Three renderers:** Dense reuses `render_supermap()`/`render_zoom()`. JSON builds structured representation from `load_primitive()`. Pretty formats human-readable markdown with status emoji. All correctly import from engine via lazy loading.

**JSON representation:** `_supermap_to_json()` iterates SHOW_ORDER → NAMESPACE, builds per-namespace resource lists with `codex://workspace/` URIs. Format compatible with MCP resource structure.

**Pretty renderer:** `_format_pretty_primitive()` extracts status/priority for display, shows emoji indicators, truncates long values at 100 chars, skips redundant fields (primitive, status, priority, coordinate). Well-organized.

**tmux integration:** `start_panes()` kills existing session first (clean start), creates 3 panes with `watch -n2` polling, applies `even-horizontal` layout. `stop_panes()` reports success/failure.

**Graceful degradation:** All `--render` modes work standalone without tmux. Only `--start` requires tmux. If tmux isn't installed, `subprocess.run` will fail gracefully with error output.

**CLI:** argparse with `--start`, `--stop`, `--render`, positional `coord`. `--start` uses `nargs='?'` to accept optional inline coord.

### 4. Engine Modifications (+179 lines) — PASS

**Sort mode infrastructure (lines 81-190):** `SORT_MODES` dict with lambda sort keys. `_SORT_MODE_CYCLE` for `e0x` cycling. `_apply_sort_mode()` correctly skips for alpha (already sorted) and shuffle (random.shuffle). Batch frontmatter reading for priority/recent sorts.

**`e0x` dispatch (lines 3962-3975):** Mode-switch handled BEFORE orchestration engine check — correct, since it doesn't need orchestration. F-label tracks `Δ engine.sort_mode old→new`. Auto-renders supermap after switch. R-label tracking via `tracker.track_render()`.

**`--shuffle` one-shot (lines 4259-4272):** Temporarily sets shuffle mode, renders, restores. Closure-based `_restore_shuffle()` function reads `_one_shot_shuffle` from enclosing scope. Works correctly.

**`--boot` delegation (lines 4280-4290):** Delegates to `CodexMaterializer.boot()` with `ImportError` fallback to inline boot — backwards compatible during transition.

**get_primitives integration (line 272):** `_apply_sort_mode()` applied after all other sorting, correctly skipped for modes namespace (`prefix != 'e'`).

**No regressions:** Sort mode is `'alpha'` by default, which returns `items` unchanged — existing behavior preserved. Module-level `_load_persisted_sort_mode()` only activates if state file exists.

---

## FLAGS

### FLAG-1 (MED): `_read_supermap_from_codex` parsing is fragile

The supermap extraction from `CODEX.codex` (materialize.py:239-261) finds the end of supermap content by searching for `\n---\ntype:`. If the supermap text itself ever contains that exact pattern (e.g., in a primitive slug or body), the split would be incorrect.

**Current risk:** LOW — supermap output doesn't contain `---\ntype:` patterns. But as workspace content grows, this could surprise.

**Recommendation:** Use a more robust separator. Options:
- (a) Use a unique sentinel like `\n--- SECTION:diff ---\n` instead of bare `---`
- (b) Parse the CODEX.codex as a proper multi-doc YAML stream (each `---` starts a new doc with its own frontmatter)
- (c) Store supermap and diff as separate files (`CODEX.codex` + `CODEX_DIFF.codex`)

The fallback to `render_supermap()` on parse failure (line 261) means this won't crash — just wastes a re-render.

### FLAG-2 (LOW): `_supermap_to_json` caps entries at 20 silently

In `codex_panes.py:152`, `resources[:20]` truncates namespace entries without indicating truncation. A namespace with >20 primitives (e.g., memory entries, lessons) would show incomplete data in the JSON pane.

**Recommendation:** Add a `"truncated": true, "total": len(entries)` field when entries exceed 20, or increase the cap. The pretty renderer already handles this correctly with `"... and N more"` (line 172).

### FLAG-3 (LOW): `--shuffle` in main() re-declares `global _current_sort_mode`

Lines 4264 and 4271 both declare `global _current_sort_mode` — once in the outer scope and once inside the nested `_restore_shuffle()` function. This works but is slightly confusing. The nested `global` is necessary for Python's scoping rules (closures can read but not reassign enclosing vars without `global`/`nonlocal`), so it's correct — just worth noting.

**No fix needed** — this is a style observation, not a bug.

---

## Verification Checklist

### MCP Server
- [x] `resources/list` enumerates all active primitives + supermap + memory
- [x] `resources/read` resolves URI → coordinate → codex-formatted content
- [x] `resources/read` raises ValueError on invalid URI
- [x] `tools/list` returns 5 tools matching design spec
- [x] `tools/call` dispatches to engine operations with stdout capture
- [x] JSON-RPC error handling (invalid method, missing params, internal error)
- [x] Content-type `application/x-codex` for resource reads
- [x] Per-session RenderTracker with dedicated state file
- [x] Sync implementation (no async overhead)

### Live Mode-Switch
- [x] `e0x` cycles through sort modes via `_SORT_MODE_CYCLE`
- [x] `e0x shuffle` / `e0x alpha` / `e0x priority` / `e0x recent` / `e0x reverse` all work
- [x] `e0x reset` → alpha
- [x] `e0x` auto-renders supermap via `render_supermap()` + `track_render()`
- [x] `--shuffle` applies one-shot without persisting
- [x] F-label tracks `Δ engine.sort_mode old→new`
- [x] Sort mode persists across CLI invocations via `materialize_hashes.json`
- [x] Invalid mode returns error with valid options
- [x] Added to `SINGLE_OPS` for clean dispatch
- [x] Modes namespace (`e`) excluded from sort mode (always coord-sorted)

### Reactive Materialization
- [x] `--boot` generates CODEX.codex + injects into AGENTS.md
- [x] Hash-based change detection (SHA-256 truncated to 12 chars)
- [x] Diff output shows Δ/+/- for changed/added/removed primitives
- [x] `materialize_affected()` updates hash state incrementally
- [x] `--full` forces complete re-materialization
- [x] First-run graceful (empty old_prim_hashes → no diff)
- [x] Timestamp stripping in `_hash_content()` prevents false diffs
- [x] `--boot` fallback in engine if materializer not importable

### Multi-Pane Rendering
- [x] `--render dense` produces valid engine output
- [x] `--render json` produces valid JSON
- [x] `--render pretty` produces readable markdown with emoji
- [x] `--start` creates tmux session with 3 panes
- [x] `--stop` kills the tmux session
- [x] `--start coord` renders specific coordinate in all formats
- [x] Pretty output includes status emoji and field formatting
- [x] Standalone render works without tmux

### Integration
- [x] Post-mutation materialization in `execute_edit()` (try/except)
- [x] Post-mutation materialization in `execute_create()` (try/except)
- [x] `--boot` delegates to materializer with ImportError fallback
- [x] Sort mode persists via shared `materialize_hashes.json`
- [x] No regressions to existing V2 functionality (alpha sort default, unchanged APIs)

---

## Conclusion

Clean implementation of all four V3 modules. All 5 design FLAGs from the design review are addressed. The code is well-structured, properly separated, and introduces no regressions. The ~179 lines added to `codex_engine.py` are surgical — sort mode infrastructure, `e0x` dispatch, one-shot shuffle, and boot delegation.

**FLAGs summary:**
- FLAG-1 (MED): Fragile `CODEX.codex` parsing — mitigated by fallback to `render_supermap()`
- FLAG-2 (LOW): JSON pane silently caps at 20 entries per namespace
- FLAG-3 (LOW): Redundant `global` declaration in nested function — correct but stylistically noisy

None are blockers. All are minor polish items for future iterations.

**APPROVED for phase completion.**
