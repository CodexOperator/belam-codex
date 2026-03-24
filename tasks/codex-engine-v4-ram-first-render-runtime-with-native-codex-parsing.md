---
primitive: task
status: in_pipeline
priority: high
created: 2026-03-23
owner: belam
depends_on: []
upstream: [codex-engine-v3-legendary-map, codex-engine-v3-temporal-mcp-autoclave]
downstream: [ram-git-worktree-bootstrap, ram-git-diff-pipeline, ram-git-sync-daemon, ram-git-undo-primitive, ram-git-pipeline-signaling]
tags: [codex-engine, render-engine, ram, codex-format, research]
notes: D7 deliverables extracted into 5 standalone sub-tasks (2026-03-24). This task retains D1-D6 (RAM-first render runtime). D7.4 (agent branch isolation) deferred to Phase 3.
pipeline: codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing
---

# Engine Render Modes: RAM-First Render Runtime

## Vision

The codex engine transitions from a CLI tool (read files → process → output) to a **persistent runtime** that agents live inside. The render engine (codex_render.py, 1573L from V3) becomes the single source of truth. Disk is persistence, not authority.

## Architecture

```
[Render Engine — RAM Tree (331+ nodes)]
       ↑ write          ↓ diff
   [Agent A]        [Agent B]
       ↑               ↑
   [UDS attach]    [UDS attach]
       ↓               ↓
   [Auto-flush to disk per turn]
```

### Core Principle: RAM is Truth, Disk is Persistence
- All reads come from RAM tree (no file I/O on the hot path)
- All writes go to RAM first, diff computed immediately
- Disk flush happens per-turn (normal mode) — transparent to agents
- Test mode: RAM stays isolated until explicit merge (like uncommitted git branch)
- No stale state files (render tracker, anchor, etc.) — engine memory IS the state

## Deliverables

### D1: RAM-First Write Path
- `codex_engine.py` edit operations (`e1`, `e2`, `e3`) write to render engine RAM via UDS
- Render engine computes diff immediately (no inotify round-trip)
- Auto-flush to disk after each write (fire-and-forget)
- Fallback: if engine not running, write to disk directly (graceful degradation)

### D2: Native .codex Parsing
- Render engine natively reads/writes `.codex` format (frontmatter + coordinate tree)
- CODEX.codex becomes a snapshot of the RAM tree (like a lockfile)
- Parse the existing format (~50 lines) — no format changes needed
- On engine start: load from .codex if fresher than disk scan, else rebuild

### D3: UDS Session Protocol Extensions
- `write` command: agent sends coordinate edit via UDS, engine applies to RAM
- `subscribe` command: agent registers for push notifications on changes
- `context` command: returns assembled context (scaffold + supermap + diff since attach)
- Per-session anchors: each agent has its own diff baseline (already built in V3)

### D4: Cockpit Plugin — UDS-Only Path
- `before_prompt_build` queries engine via UDS exclusively (no subprocess fallback)
- If engine is down, start it (already built) then query
- Remove all `codexExec()` subprocess calls — UDS is the only path
- Result: ~1ms context injection instead of ~300ms

### D5: .codex Stack Integration
- OpenClaw workspace discovery reads `.codex` for primitive metadata
- Bootstrap hook reads from engine (via UDS) instead of materializing from disk
- `R` CLI queries engine for all views (already partially done)
- Single source: engine → .codex snapshot → disk files (in that order)

### D6: Test Mode as Branch Semantics  
- Normal: RAM → auto-flush → disk (transparent)
- Test: RAM → hold (like uncommitted branch) → explicit commit/discard
- Both modes share the same RAM tree structure — test mode just suppresses flush
- Replaces dulwich dependency with simpler flag-based isolation

## Key Questions for Architect
1. Should the engine expose a REST-like HTTP API in addition to UDS? (for remote dashboard, canvas)
2. How does the RAM tree handle concurrent writes from 2 agents? (locking per-node vs per-namespace)
3. Should .codex snapshots be versioned (git-like) or just latest-state?
4. What happens on engine crash — rebuild from disk files or from .codex snapshot?

## Success Criteria
- [ ] Agent edit → diff visible to other attached agents in <5ms
- [ ] Zero subprocess calls in the hot path (all UDS)
- [ ] .codex file accurately reflects RAM tree state
- [ ] Engine restart recovers full state from disk in <1s
- [ ] Test mode: full session of edits, commit or discard cleanly

## D2

D2 is simplified: call existing codex_codec.py on startup to hydrate RAM tree from .codex. ~5 lines integration, not a standalone deliverable.

## D5

D5 revised: NO direct OpenClaw integration. Engine is authoritative for our agents only (via cockpit plugin UDS). Disk files remain real files that auto-flush from RAM. OpenClaw reads normal files — never needs to know about the engine. This avoids breaking other OpenClaw features that expect standard workspace files.

## D6

D6 revised: KEEP dulwich for test mode. Dulwich provides real branch semantics (merge, diff-between-branches, discard) that a simple flush-suppression flag cannot replicate. The render engine already uses dulwich — no changes needed here, just ensure it works with the RAM-first write path.


## D7: RAM Git Worktree as Agent Filesystem

### Vision
Agents don't know they're in RAM. The workspace resolves through symlinks to a git repo on tmpfs. Every file write is a git object. The render engine observes the git tree instead of the filesystem.

### Architecture
```
/dev/shm/codex/                    ← git repo in tmpfs (working tree + .git)
  ├── tasks/
  ├── decisions/
  ├── lessons/
  ├── memory/
  ├── pipeline_builds/
  └── .git/                        ← full git objects, all in RAM

~/.openclaw/workspace/
  ├── tasks/ → /dev/shm/codex/tasks/          ← symlinks
  ├── decisions/ → /dev/shm/codex/decisions/
  ├── lessons/ → /dev/shm/codex/lessons/
  └── ...                                      ← non-primitive dirs stay on disk
```

### Sub-deliverables

**D7.1: RAM repo bootstrap**
- On engine start: `git clone --local workspace → /dev/shm/codex/` (primitive dirs only)
- Symlink primitive namespace dirs from workspace → tmpfs
- Engine reads git tree directly (replaces inotify watcher entirely)
- `git diff HEAD~1` replaces the inotify→queue→flush chain

**D7.2: Git-native diff pipeline**
- `post-commit` hook → pings render engine UDS → diffs flow to agents next turn
- Replaces: inotify watches, change queue, flush worker
- Coalescing is free (git handles atomic commits)
- Ordering is free (commit sequence)

**D7.3: Background sync daemon**
- Periodically pushes RAM git → disk git for persistence
- Configurable interval (default: every 60s + on agent session end)
- Crash recovery: clone disk → RAM on boot (systemd ExecStartPre)
- Sync is `git push` — fast, incremental, atomic

**D7.4: Agent branch isolation (optional, Phase 3)**
- Each pipeline agent works on `{role}/{pipeline}` branch
- Coordinator sees all branches — merge conflicts = coordination signals
- Merge to main = accepted work
- Discard branch = rollback

**D7.5: Pipeline turn-by-turn signaling**
- Instant wake on `_state.json` commit (pattern-match in post-commit hook)
- Directive file convention: coordinator writes `_directive.md`, agent sees as diff
- Threshold tuning: state file changes bypass the 10-diff accumulator

### Key Properties
- **Flush isolation preserved:** each agent's turn pokes independently — no contention
- **Nice mode still works:** queue is now git's working tree; flush = commit
- **Volatile risk mitigated:** sync daemon + systemd ExecStartPre recovery
- **Graceful degradation:** if tmpfs unavailable, fall back to disk-direct (current behavior)

### D7.6: Undo Primitive
- Turn boundary = commit boundary (cockpit plugin fires auto-commit on turn end)
- `e1 undo` → `git reset --hard HEAD~1` on RAM repo — instant, atomic rollback
- `e1 undo N` → roll back N turns
- Undo is RAM-only until next sync — disk stays clean as "are you sure?" boundary
- Adds to coordinate grammar: agents get undo as a first-class action

### D7.7: Ping/Pong Granularity Modes
Configurable signaling frequency between agents and coordinator:

| Mode | Behavior | Use case |
|------|----------|----------|
| `batch` | Current behavior — diffs accumulate, 10-threshold wake | Background pipelines, low priority |
| `stage` | Wake on `_state.json` commit only | Normal pipeline flow |
| `turn` | Every agent commit wakes coordinator | Active debugging, pair-steering |
| `live` | post-commit hook fires on every write (sub-turn) | Real-time observation |

- Mode set per-pipeline in `_state.json` (`ping_mode: batch|stage|turn|live`)
- post-commit hook reads mode and routes: skip / wake coordinator / wake all watchers
- Default: `stage` (sane middle ground)

### D7.8: Read/Write Routing Architecture

**Decision: Symlinks — agent home IS RAM.**

```
Agent perspective:     ~/workspace/tasks/foo.md  (reads AND writes)
OS resolves to:        /dev/shm/codex/tasks/foo.md
Agent doesn't know.

Static files stay on disk (not symlinked):
  AGENTS.md, SOUL.md, IDENTITY.md, USER.md,
  MEMORY.md, HEARTBEAT.md, skills/, scripts/,
  commands/, modes/, templates/, docs/

Primitive dirs symlinked to RAM:
  tasks/, decisions/, lessons/, memory/entries/,
  pipeline_builds/, pipelines/, goals/, knowledge/,
  projects/, workspaces/
```

- Reads from RAM = always freshest state (includes other agents' uncommitted writes)
- Writes to RAM = instant, git-tracked, diffable
- Static config files stay on disk — no symlink needed, rarely change
- Sync daemon is the only disk writer (periodic + on session end)
- Crash recovery: `ExecStartPre=git clone disk → RAM` in systemd unit

**Why not split R/W paths:**
- Explicit routing contaminates every agent prompt and skill
- Scales poorly — every new agent needs the convention
- Symlinks are invisible — agents just use standard filesystem ops
- RAM reads are faster anyway (no reason to read from disk)

### Success Criteria
- [ ] Agent file writes resolve to RAM via symlinks (<1ms I/O)
- [ ] `git diff` replaces inotify for all diff generation
- [ ] Sync daemon maintains <60s staleness on disk
- [ ] Engine restart from cold (disk clone → RAM) in <3s
- [ ] Pipeline state changes wake coordinator within 1 turn
- [ ] `e1 undo` rolls back last turn in <10ms
- [ ] Ping mode configurable per-pipeline, default `stage`
- [ ] Zero agent-facing changes — symlinks invisible to all existing prompts/skills

## Phase 2 Notes
- .codex file YAML parsing fails on some frontmatter blocks — codec needs normalization pass before feeding to yaml.safe_load
- Use codex_codec.py as canonical parser (it already handles edge cases)
- Render engine currently falls back to disk scan on .codex parse failure — acceptable for now
- Systemd service set up: codex-render.service (auto-restart, survives reboots)
- Stale UDS socket cleanup needed on startup (check and remove before binding)
