## OpenClaw Infra Cleanup — 2026-04-13

This archive bucket contains stale or historical OpenClaw infrastructure material that was moved out of the active workspace during the 2026-04-13 cleanup pass.

What was moved here:
- Legacy scripts and backup files superseded by current runtime/orchestration code
- Historical cockpit/render-engine guides and stale memory-cron documentation
- Archived infrastructure pipeline definitions and their matching `pipeline_builds/` artifacts
- Completed or superseded infrastructure task documents
- Old extension backup material

What was intentionally left active:
- Current runtime entrypoints such as `scripts/pipeline_orchestrate.py`, `scripts/pipeline_autorun.py`, `scripts/reactive_daemon.py`, and `plugins/codex-cockpit/`
- Active or still-open tasks/pipelines
- The `machinelearning/` subtree, including its `research/pipeline_builds/`, which was explicitly deferred for a later cleanup pass

Reason for this archive:
- Reduce clutter in active infrastructure paths
- Make future refactors target the current architecture instead of several historical layers at once
- Preserve all historical material in one recoverable location
