# TODO: repoint supermap/render/reactive stack from legacy OpenClaw runtime to belam-codex/Hermes-native paths

Timestamp: 2026-04-14 UTC
Controller: Belam (Hermes)

## Why this exists
We mapped the currently running `.openclaw/workspace` stack using GitNexus plus live system inspection. The repo can render supermap directly, but the installed background/runtime chain is still mostly wired to legacy OpenClaw paths. The goal is to make the managed stack resolve through `/home/ubuntu/.hermes/belam-codex` and stay consistent across bootstrap, services, plugins, and runtime files.

## GitNexus findings from /home/ubuntu/.openclaw/workspace

### 1) RenderTracker is central render-state infrastructure
Command used:
- `gitnexus context -r workspace RenderTracker`
- `gitnexus impact -r workspace RenderTracker --direction upstream`

Key result:
- Symbol: `Class:scripts/codex_engine.py:RenderTracker`
- Risk if changed: `MEDIUM`
- Direct dependents include:
  - `scripts/codex_engine.py:get_render_tracker`
  - `scripts/codex_engine.py:_render_dashboard`
  - `scripts/codex_mcp_server.py:tracker`
- Imported by:
  - `scripts/render_supermap.py`
  - `scripts/codex_watch.py`
  - `scripts/codex_ram.py`
  - `scripts/codex_panes.py`
  - `scripts/codex_mcp_server.py`
  - `scripts/codex_materialize.py`
  - `scripts/archived/codex_render.py`

Interpretation:
- RenderTracker changes are not isolated. If you touch its semantics, audit all render helpers and MCP/materialize/watch consumers.

### 2) ReactiveDaemon is relatively isolated
Command used:
- `gitnexus context -r workspace ReactiveDaemon`
- `gitnexus impact -r workspace ReactiveDaemon --direction upstream`

Key result:
- Symbol: `Class:scripts/reactive_daemon.py:ReactiveDaemon`
- Risk if changed: `LOW`
- Direct upstream references are mainly:
  - `scripts/reactive_daemon.py:main`
  - import relationship via `scripts/codex_engine.py`

Interpretation:
- Service/path repointing around reactive daemon is safer than deep render-core changes.

### 3) UDS path in codex_engine is already mostly retired
Command used:
- `gitnexus context -r workspace _try_uds_query --file scripts/codex_engine.py`

Key result:
- `_try_uds_query` is a stub returning `None`
- only used by `_try_uds_edit` and `_try_uds_supermap`

Interpretation:
- direct on-demand supermap rendering is now the real working path
- old socket-driven assumptions should be minimized or removed unless still needed for compatibility

## Live system findings

### Broken render service
Installed unit file:
- `/home/ubuntu/.config/systemd/user/codex-render.service`

Current contents:
- `WorkingDirectory=/home/ubuntu/.openclaw/workspace`
- `ExecStart=/usr/bin/python3 scripts/codex_render.py --force --mode nice`

Problem:
- `scripts/codex_render.py` does not exist in `.openclaw/workspace`
- service is crash-looping
- journal shows repeated failure opening `/home/ubuntu/.openclaw/workspace/scripts/codex_render.py`

### Still-running reactive service on legacy path
Installed unit file:
- `/home/ubuntu/.config/systemd/user/openclaw-reactive.service`

Current contents include:
- `ExecStart=/usr/bin/python3 %h/.openclaw/workspace/scripts/reactive_daemon.py --loop --interval 30 --queue-spacing 1h`
- `Environment=OPENCLAW_WORKSPACE=%h/.openclaw/workspace`
- `WorkingDirectory=%h/.openclaw/workspace`

Problem:
- service is live, but still pinned to legacy OpenClaw workspace
- not using `/home/ubuntu/.hermes/belam-codex`

### Installed cockpit plugin still depends on legacy shm path
Installed file:
- `/home/ubuntu/.openclaw/extensions/codex-cockpit/index.ts`

Current behavior:
- reads supermap from `/dev/shm/openclaw/supermap.txt`
- attempts socket poke via `<cwd>/.codex_runtime/render.sock`
- falls back to legend + scaffold when file is missing

Problem:
- `/dev/shm/openclaw/supermap.txt` is currently missing
- `/home/ubuntu/.hermes/belam-codex/.codex_runtime/render.sock` is currently missing
- plugin therefore degrades to non-supermap injection

### belam-codex repo state
The repo-managed Hermes-side workspace already has:
- `bin/R`
- `scripts/install_interface_bootstrap.py`
- `local_plugins/openclaw_hooks/plugin.py`
- `plugins/codex-cockpit/index.ts`

And direct render works:
- `python3 scripts/codex_engine.py --supermap-anchor`

## What needs to change

1. Decide the canonical runtime mode
- Preferred assumption: daemonless/direct render is the primary path
- Compatibility shims may remain temporarily, but should not be the primary dependency

2. Repoint installed services away from `.openclaw/workspace`
- `~/.config/systemd/user/codex-render.service`
- `~/.config/systemd/user/openclaw-reactive.service`

3. Fix the cockpit plugin contract
Options to evaluate:
- A) make plugin call direct render in-process / via script instead of relying on shm file
- B) keep compatibility but derive a workspace-specific supermap artifact path under active workspace instead of `/dev/shm/openclaw/supermap.txt`
- C) if socket mode is truly retired, remove stale socket/shm assumptions from plugin path

4. Normalize workspace resolution
Audit and harmonize fallback order across:
- `scripts/codex_engine.py`
- `local_plugins/openclaw_hooks/plugin.py`
- `plugins/codex-cockpit/index.ts`
- `bin/R`
- `scripts/install_interface_bootstrap.py`
- installed systemd unit templates / installers

5. Ensure bootstrap installer manages the actual runtime artifacts
Installer should be able to refresh the real live paths, not just repo copies:
- `~/.local/bin/R`
- `~/.hermes/plugins/openclaw_hooks`
- `~/.openclaw/extensions/codex-cockpit`
- possibly user systemd units too, if that is intended

6. Verify end-to-end
Minimum checks after edits:
- direct render works from belam-codex
- cockpit injection path sees supermap again
- reactive daemon runs against belam-codex
- render service either works correctly or is intentionally retired/removed
- no stale hardcoded `.openclaw/workspace` runtime paths remain where belam-codex should own them

## Concrete task list for Codex

- [ ] inspect current dirty state in `/home/ubuntu/.hermes/belam-codex`
- [ ] use GitNexus impact before editing any symbol required by AGENTS.md
- [ ] compare belam-codex repo files against installed user service/plugin artifacts
- [ ] decide and document primary runtime path: direct render vs background render compatibility
- [ ] implement the minimal coherent repointing set
- [ ] update installer/bootstrap flow if needed so future installs converge automatically
- [ ] run focused verification commands
- [ ] summarize remaining questions or tradeoffs

## Questions Codex should ask Belam before risky edits
If unclear, stop and ask before proceeding:
1. Should `codex-render.service` be fully repaired, or intentionally retired in favor of direct render?
2. Should systemd user unit files be repo-managed by `install_interface_bootstrap.py` now, or left for a later step?
3. Is backward compatibility with `.openclaw/workspace` still required, or can Hermes-first become the default with only soft fallback?

## Suggested initial verification commands
```bash
cd /home/ubuntu/.hermes/belam-codex
python3 scripts/codex_engine.py --supermap-anchor >/tmp/belam-supermap.txt
systemctl --user status codex-render --no-pager --lines=40 || true
systemctl --user status openclaw-reactive --no-pager --lines=40 || true
journalctl --user -u codex-render --no-pager -n 40 || true
```
