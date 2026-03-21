---
primitive: decision
status: active
created: 2026-03-21
tags: [codex-engine, live-diffs, infrastructure, v3]
upstream: [decision/codex-engine-v1-architecture]
downstream: []
---

# Live Diff Streaming Architecture

## Context

The Codex Engine (codex_engine.py) renders the workspace supermap on-demand — agents call `belam` and pay a ~200ms Python cold-start cost on every invocation. At conversation turn-start or during heartbeats, agents need to know *what changed* since they last looked. Polling the full engine repeatedly is wasteful and brittle. The workspace has well-defined primitive directories that change predictably; we can watch the filesystem and emit R-label diffs only when something actually changes.

## Problem

Agents wake fresh each session and have no ambient awareness of concurrent changes. When Shael edits a task or a pipeline agent updates a memory entry, the coordinator doesn't know until it runs `belam` and compares. We need:
1. Near-zero idle cost monitoring (no 1/sec polling)
2. Accumulated diffs readable at turn-start without re-running the full engine
3. A clean label discipline: R-labels for view updates, F-labels reserved for agent mutations

## Decision

Implement a **Live Diff Daemon** (`scripts/codex_watch.py`) that:
- Runs as a background process (daemon mode via `belam watch`)
- Uses the `watchdog` Python library to monitor all primitive directories for filesystem events
- On file change → re-renders only the affected coordinate(s) using existing engine internals
- Writes R-label diffs to an append-only buffer file (`~/.belam_live_diffs.log`)
- Exposes a read-and-clear interface via `belam diffs`

## Architecture

### Daemon Lifecycle

```
belam watch          → starts codex_watch.py --watch in background, writes ~/.belam_watch.pid
belam watch --stop   → sends SIGTERM to PID from pidfile
belam watch --status → checks if daemon process is running
```

The daemon holds the workspace primitive index in memory. This is the key efficiency win: Python cold-start paid once at daemon launch, then filesystem events drive re-renders at near-zero marginal cost.

### Watched Directories

All primitive namespace directories relative to `$BELAM_WORKSPACE`:

| Namespace | Directory            | Prefix |
|-----------|----------------------|--------|
| tasks     | tasks/               | t      |
| decisions | decisions/           | d      |
| lessons   | lessons/             | l      |
| pipelines | pipelines/           | p      |
| commands  | commands/            | c      |
| knowledge | knowledge/           | k      |
| memory    | memory/entries/      | m      |
| daily     | memory/             | md     |

The daemon watches recursively but filters events to `.md` files only.

### Event Filtering

Ignored paths/patterns:
- `.git/` and any path containing `/.git/`
- `__pycache__/`, `*.pyc`, `*.pyo`
- Temp/swap files: `*.tmp`, `*.swp`, `*.swo`, `*~`, `.#*`
- `codex_engine.py` itself (prevents feedback loops if engine is edited)
- `codex_watch.py` itself
- `~/.belam_live_diffs.log` (the output buffer)

### Debouncing

Rapid writes (e.g., a script touching multiple fields of a primitive, or vim saving a swap then the real file) are batched with a **500ms debounce window**. After the last filesystem event for a given filepath, the daemon waits 500ms before re-rendering. This prevents duplicate diff entries for a single logical edit.

### Coordinate Resolution

When a file change event fires for path `decisions/live-diff-streaming-architecture.md`:
1. Identify the primitive directory → namespace prefix `d`
2. Call `get_primitives('d')` to get the current index
3. Find the index position of the changed slug → coordinate `d{n}`
4. If not found (new file), the coordinate is `d{len+1}` (new primitive)
5. Re-render using `render_zoom([coord])`

For memory entries (prefix `m`) in `memory/entries/`, the slug is the filename stem.
For daily files (prefix `md`) in `memory/`, pattern `YYYY-MM-DD.md` identifies them.

### R-Label Assignment

The daemon calls `get_render_tracker().track_render(content)` to assign R-labels, exactly as the main engine does. This ensures:
- R-label sequence is shared across daemon and interactive CLI invocations
- Identical re-renders produce pin references (R📌R{n})
- Diff entries carry the same label format agents already understand

**R-labels are the correct layer for daemon-emitted diffs.** The daemon observes filesystem changes initiated externally — it does not mutate primitives. F-labels are reserved for agent-initiated mutations (edits, creates, links) tracked through the main engine's `next_f_label()` mechanism.

### Diff Buffer

File: `~/.belam_live_diffs.log`

Format (JSONL — one JSON object per line):
```json
{"ts": "2026-03-21T00:41:00Z", "coord": "d12", "slug": "live-diff-streaming-architecture", "label": "R42", "diff": "R42 ╶─ d12 live-diff-streaming-architecture\n│  status: active\n│  ..."}
```

Properties:
- **Append-only** during daemon operation
- **Max 50 entries** — when limit reached, oldest entries are dropped (ring buffer semantics)
- **Read-and-clear** via `belam diffs`: reads all entries, truncates the file, prints entries

### Read-and-Clear Interface

```
belam diffs
```

Reads `~/.belam_live_diffs.log`, prints each R-label diff to stdout, then truncates the file. Atomic: uses file locking (or write-truncate) to avoid races with the daemon writer.

Output format:
```
[2026-03-21 00:41 UTC] d12 changed → R42
R42 ╶─ d12 live-diff-streaming-architecture
│  primitive: decision  status: active  created: 2026-03-21
│  tags: [codex-engine, live-diffs, infrastructure, v3]
│  upstream: d9 (codex-engine-v1-architecture)
│  downstream: —
---
(1 diff since last check)
```

If no diffs: `(no diffs since last check)`.

## Consumption (V3 — Design Only)

This section describes intended consumption patterns. **Integration is future work.**

### Turn-Start Pattern (V3 Target)

At conversation turn-start, the coordinator agent calls `belam diffs` before doing anything else. If diffs are present, it incorporates them into its working context — knowing what changed without re-rendering the full supermap.

```
# Pseudo-code for coordinator turn-start
diffs = belam diffs
if diffs:
    # Context-patch: update local understanding of changed coordinates
    process_r_label_diffs(diffs)
else:
    # No changes since last turn — supermap knowledge is current
    pass
```

### Heartbeat Pattern

Heartbeats can poll `belam diffs` to detect workspace activity and surface notable changes (new tasks created, pipeline state updates, memory entries added by other agents).

### OpenClaw Hook (Future)

A future OpenClaw session hook could call `belam diffs` at turn-start and inject the output directly into session context, making diff awareness transparent to agents without them needing to call it explicitly.

### Why Not Poll the Full Engine?

| Approach | Cost per check | Idle cost |
|---|---|---|
| `belam` on demand | ~200ms cold-start | Zero |
| Poll full engine 1/sec | ~200ms × 60 = 12s/min wasted | 100% CPU |
| **Live diff daemon** | ~0ms (buffer read) | Near-zero (event-driven) |

The daemon holds the index in memory. On filesystem events it re-renders one coordinate (~5ms). At idle, the watchdog observer uses OS-native filesystem event APIs (inotify on Linux) — no polling.

## Dependencies

**Required: `watchdog` Python library**

```bash
pip3 install watchdog
```

⚠️ As of 2026-03-21, `watchdog` is **NOT installed** in this environment. The daemon scaffold (`codex_watch.py`) is written but will fail at import time until `watchdog` is installed. Add to `requirements.txt` or install before running.

Watchdog uses `inotify` on Linux (arm64 Oracle Cloud instance), which is efficient and well-supported.

## Alternatives Considered

### Full Re-render on Every Turn
Simple but expensive. 200ms cold-start × many turns = noticeable latency. Also provides no history — agent sees current state, not what changed.

### Git-based Diffing
Could watch git diffs. But requires git commits to be meaningful, and doesn't integrate with R-label tracking. Overkill for this use case.

### SQLite Change Journal
More robust for high-write scenarios. Complexity not justified for a workspace with dozens of primitives updated infrequently.

### inotify Direct (without watchdog)
Would require OS-specific code. Watchdog abstracts this cleanly and handles edge cases (vim rename-on-save, atomic writes).

## Consequences

**Positive:**
- Near-zero idle cost ambient awareness
- R-label continuity across interactive and daemon renders
- Agents can orient themselves at turn-start with `belam diffs` instead of full supermap re-render
- Batched diff history survives across short gaps in daemon uptime

**Negative / Risks:**
- Daemon requires `watchdog` dependency (currently missing)
- PID-file management is simplistic; if host reboots, stale pidfile may confuse status checks
- Buffer overflow (>50 entries) silently drops oldest diffs — agents may miss changes during high-activity periods
- Daemon must be started separately; not auto-started by OpenClaw (future work)

## Implementation Status

- [x] Design document (this file)
- [x] Daemon scaffold: `scripts/codex_watch.py`
- [x] CLI wiring: `watch` and `diffs` in `ACTION_REGISTRY`
- [x] Command primitives: `commands/watch.md`, `commands/diffs.md`
- [ ] `watchdog` installed in environment
- [ ] Turn-start consumption integration (V3)
- [ ] OpenClaw hook injection (future)
- [ ] Auto-start on workspace boot (future)
