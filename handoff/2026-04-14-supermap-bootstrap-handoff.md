# Handoff: supermap/bootstrap portability (Hermes + OpenClaw)

Timestamp: 2026-04-14 02:50 UTC
Repo: `/home/ubuntu/.hermes/belam-codex`

## Goal completed
Make supermap + cockpit context injection reproducible across fresh sessions/machines by moving bootstrap logic into repo-managed install flow.

## What was done

### 1) Added repo-managed R wrapper source
- Added: `bin/R`
- Mirrors the working local wrapper behavior with Hermes-first workspace resolution:
  1. `OPENCLAW_WORKSPACE`
  2. `BELAM_WORKSPACE`
  3. `~/.hermes/belam-codex`
  4. `~/.openclaw/workspace`
  5. `$PWD` when `scripts/codex_engine.py` exists
  6. fallback `~/.hermes/belam-codex`

### 2) Added unified installer script
- Added: `scripts/install_interface_bootstrap.py`
- Installs/refreshes:
  - `~/.local/bin/R`
  - `~/.hermes/plugins/openclaw_hooks`
  - `~/.openclaw/extensions/codex-cockpit`

### 3) Hardened Hermes plugin workspace detection
- Modified: `local_plugins/openclaw_hooks/plugin.py`
- `_workspace()` now resolves via env + cwd + Hermes/legacy defaults (instead of only `WORKSPACE` / repo-relative assumption).
- subprocess calls now set `BELAM_WORKSPACE` and `OPENCLAW_WORKSPACE` to selected workspace for consistent rendering.

### 4) Removed hardcoded legacy socket path in cockpit plugin
- Modified: `plugins/codex-cockpit/index.ts`
- UDS connect now uses workspace-relative socket:
  - `<cwd>/.codex_runtime/render.sock`
  - instead of hardcoded `~/.openclaw/workspace/.codex_runtime/render.sock`

## Validation run

### Install command executed
```bash
cd /home/ubuntu/.hermes/belam-codex
python3 scripts/install_interface_bootstrap.py
```

Observed output:
- installed R wrapper -> `/home/ubuntu/.local/bin/R`
- installed Hermes plugin -> `/home/ubuntu/.hermes/plugins/openclaw_hooks`
- installed OpenClaw plugin -> `/home/ubuntu/.openclaw/extensions/codex-cockpit`

### Supermap/legend verification
`R 0` was validated to include:
- `Codex Engine Supermap`
- `# ⚡ Belam`
- `## How to Use the Supermap`

## Current git status snapshot
```text
M local_plugins/openclaw_hooks/plugin.py
 M plugins/codex-cockpit/index.ts
 M state/supermap_anchor.json
?? bin/
?? handoff/
?? scripts/install_interface_bootstrap.py
```

Notes:
- `state/supermap_anchor.json` is a runtime artifact (pre-existing dirty file in this flow).
- `handoff/` was already untracked before these changes.

## Quick repro for next session
```bash
which R
sed -n '1,40p' /home/ubuntu/.local/bin/R
cd /home/ubuntu/.hermes/belam-codex
python3 scripts/install_interface_bootstrap.py
R 0
```

## Next optional step
Extend installer with Codex CLI / Claude Code adapter install targets so the same context-injection stack is one command across all interfaces.
