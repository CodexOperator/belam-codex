---
primitive: task
status: done
priority: high
created: 2026-03-24
owner: belam
depends_on: []
upstream: [scrap-r-labels-keep-f-labels-as-raw-git-diff]
downstream: [ram-git-s1-tmpfs-repo-and-symlinks]
tags: [infrastructure, codex-engine, simplification, builder-first]
pipeline: render-engine-simplification
project: codex-engine
pipeline_type: builder-first
pipeline_template: 
current_stage: 
pipeline_status: in_pipeline
launch_mode: queued
---
# Render Engine Simplification — Strip R/F Label Pipeline

## Description

Remove the R/F label diff processing pipeline, inotify change detection, HeartbeatTrigger, and DiffEntry content system from the render engine. This is pure subtraction — no new features, just cleanup.

Must complete before RAM git work begins (S1-S4 depend on a simplified render engine).

## Builder Spec

### Remove from `scripts/codex_render.py`:
1. **DiffEntry class** and all content storage logic
2. **R-label generation** — any code that produces `R[...]` formatted lines
3. **F-label formatting** — the formatted `F[...]: | --- | ...` content injection
4. **HeartbeatTrigger class** — the thread that polls for F-label count and fires webhook wakes
5. **inotify diff accumulation** — the watcher chain that feeds DiffEntry creation
6. **`my_diff` and `diff` command handlers** that serve formatted R/F output (or simplify to stubs that return empty)

### Keep in `scripts/codex_render.py`:
1. **Supermap rendering** from CODEX.codex — the `render` command
2. **Coordinate resolution** — resolving `t1`, `d5`, etc. to file paths
3. **Status/health endpoints** — `--status`, liveness checks
4. **UDS socket server** — the communication layer stays
5. **Engine lifecycle** — start, stop, PID file management

### Remove from cockpit plugin (if accessible):
1. **Diff injection logic** — any code that requests/formats R/F label diffs from the render engine
2. **`include_content` parameter** — no longer needed without R/F label split
3. Keep: supermap injection, coordinate grammar handling

### Cleanup:
1. Remove dead imports after stripping code
2. Update any docstrings/comments referencing R/F labels
3. Run the render engine after changes to verify it starts and serves supermap correctly

## Files to Modify
- `scripts/codex_render.py` — primary target
- Cockpit plugin if agent has write access (document changes needed if not)

## Reference Files
- `decisions/scrap-r-labels-keep-f-labels-as-raw-git-diff.md` — governing decision
- `decisions/r-f-label-split-by-agent-role.md` — what's being superseded (understand what to remove)
- `decisions/diff-triggered-heartbeat-architecture.md` — HeartbeatTrigger design (understand what to remove)
- `lessons/diffentry-content-field-for-f-label-display.md` — DiffEntry context (understand what to remove)

## Success Criteria
- [ ] Render engine starts cleanly after removal
- [ ] `python3 scripts/codex_render.py --status` returns healthy
- [ ] Supermap rendering works unchanged
- [ ] Coordinate resolution works unchanged
- [ ] No R-label or F-label output produced anywhere
- [ ] No inotify watches on primitive dirs
- [ ] HeartbeatTrigger class fully removed
- [ ] DiffEntry class fully removed
