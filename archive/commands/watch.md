---
primitive: command
name: watch
status: active
created: 2026-03-21
description: Start, stop, or check the status of the live diff daemon (codex_watch.py)
usage: R watch [--stop | --status]
script: codex_watch.py
tags: [codex-engine, live-diffs, daemon, v3]
---

# watch — Live Diff Daemon

Manages the `codex_watch.py` background daemon that monitors all primitive directories for filesystem changes and emits R-label diffs to `~/.belam_live_diffs.log`.

## Usage

```bash
R watch            # Start the daemon (backgrounded automatically)
R watch --stop     # Stop a running daemon
R watch --status   # Check if daemon is running + buffer size
```

## What It Does

The daemon uses the `watchdog` library (inotify on Linux) to watch all primitive directories:
- `tasks/`, `decisions/`, `lessons/`, `pipelines/`, `commands/`, `knowledge/`, `memory/entries/`, `memory/`

On `.md` file change (debounced 500ms):
1. Identifies the affected coordinate (e.g. `d12`)
2. Re-renders it using `render_zoom()` from codex_engine
3. Assigns an R-label via `RenderTracker`
4. Appends the diff to `~/.belam_live_diffs.log`

## Key Details

- **R-labels only** — the daemon observes external filesystem changes, not agent mutations
- **F-labels** are reserved for agent-initiated edits via `R edit`
- **Debounced**: 500ms after last filesystem event before re-rendering
- **Buffer max**: 50 entries (oldest dropped if exceeded)
- **PID file**: `~/.belam_watch.pid`

## Dependency

Requires `watchdog` Python library:
```bash
pip3 install watchdog
```

## See Also

- `R diffs` — read accumulated diffs
- `decisions/live-diff-streaming-architecture.md` — full design rationale
