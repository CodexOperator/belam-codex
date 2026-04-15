---
primitive: decision
status: accepted
date: 2026-04-15
context: Workspace moved from ~/.openclaw/workspace to ~/.hermes/belam-codex but plugins had hardcoded old paths
alternatives:
- Env var only (fragile without validation)
- Symlink old path to new (hides the problem)
- Unified cascade with existence validation
rationale: Cascade with validation prevents silent resolution to wrong directory when only one component gets updated
consequences:
- R wrapper, openclaw_hooks plugin.py, and codex-cockpit index.ts all use same resolution order
- setup_workspace.sh bootstraps all three from repo
- UDS socket path in codex-cockpit now workspace-relative
upstream: []
downstream: []
tags: [instance:main, workspace, hermes, migration]
---

# hermes-first-workspace-resolution-cascade

## Context

When the workspace moved from `~/.openclaw/workspace` to `~/.hermes/belam-codex`, the R CLI wrapper was patched with a resolution cascade. But the plugins (openclaw_hooks Python plugin and codex-cockpit TypeScript plugin) still had hardcoded paths to the old location, causing silent failures.

## Decision

All components that resolve the workspace path use the same ordered cascade:
1. `OPENCLAW_WORKSPACE` env var (explicit override)
2. `BELAM_WORKSPACE` env var (explicit override)
3. `~/.hermes/belam-codex` (preferred default, validated by `scripts/codex_engine.py` existence)
4. `~/.openclaw/workspace` (legacy fallback, validated)
5. `CWD` if `scripts/codex_engine.py` exists
6. Final fallback: `~/.hermes/belam-codex`

## Consequences

- All three components (R wrapper, Python plugin, TS plugin) share the same resolution logic
- `setup_workspace.sh` bootstrap script installs all from repo in one command
- UDS socket path in codex-cockpit is now workspace-relative instead of hardcoded
