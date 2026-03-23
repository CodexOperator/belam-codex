---
primitive: command
name: diffs
status: active
created: 2026-03-21
description: Read accumulated live diffs since the last check (read-and-clear)
usage: R diffs
script: codex_watch.py
tags: [codex-engine, live-diffs, v3]
lm_include: true
---

# diffs — Read Accumulated Live Diffs

Reads and clears the diff buffer written by the `codex_watch` daemon. Call this at conversation turn-start to orient yourself to recent workspace changes without re-rendering the full supermap.

## Usage

```bash
R diffs
```

## Output

If diffs are present:
```
[2026-03-21 00:41 UTC] d12 changed → R42
R42 ╶─ d12 live-diff-streaming-architecture
│  primitive: decision  status: active  created: 2026-03-21
│  ...
---
(1 diff since last check)
```

If no diffs:
```
(no diffs since last check)
```

## Semantics

- **Read-and-clear**: each call empties the buffer. Diffs are not repeated.
- **Buffer size**: max 50 entries. If the daemon was running and many changes occurred since last read, oldest entries may have been dropped.
- **R-labels**: diffs carry R-labels from the shared `RenderTracker` — pin references (R📌R{n}) appear if a coordinate was re-rendered to an identical state.

## When To Use

- **Turn-start**: call before reading CODEX.codex to patch your understanding of recent changes
- **Heartbeat**: check for workspace activity between sessions
- **After long gaps**: if the daemon ran overnight, read diffs to catch up on changes

## Requires

The `codex_watch` daemon must be running (`R watch`) for diffs to accumulate.
If the daemon is not running, the buffer will be empty.

## See Also

- `R watch` — start the live diff daemon
- `decisions/live-diff-streaming-architecture.md` — full design rationale
