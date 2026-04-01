# OpenClaw Cockpit Refactor Guide

## Overview

This document describes the V5 cockpit refactor: a comprehensive upgrade to the OpenClaw coordinate-addressable multi-agent orchestration system. The refactor adds **reactive field-change triggers**, **programmable pipeline lifecycle**, **dynamic persona rendering**, and **cross-mode integration** — all driven by editing `.md` frontmatter fields.

**Core principle**: `.md` frontmatter is the single source of truth. Change a field, trigger an action.

---

## Architecture Changes

### Before (V4)
- Pipeline operations required explicit script calls (`pipeline_orchestrate.py`, `launch_pipeline.py`)
- Task and pipeline state tracked in dual `.md` + `_state.json` with drift risk
- Persona rendering hardcoded in `PERSONA_CONFIGS` dict inside `codex_engine.py`
- E-modes were siloed: e1 edits couldn't trigger e0 orchestration
- No reactive behavior on frontmatter field changes
- No queue management or cadence control

### After (V5)
- `e1` field edits trigger orchestration hooks automatically (pipeline launch, rewind, reset)
- `.md` frontmatter is authoritative; `_state.json` is a derived detail cache
- Persona configs loaded dynamically from persona `.md` files with template overrides
- Cross-mode integration: e3 creates scripts consumable by e2, hooks registerable across all surfaces
- Reactive daemon polls for external changes every 30s
- Queue cadence controllable via `e0 cadence` (persisted, daemon reads live)

---

## New Files

### `scripts/post_edit_hooks.py`
**Purpose**: Reactive hook registry. When `execute_edit()` modifies frontmatter, hooks fire automatically.

**5 registered hooks**:

| Hook | Trigger | Action |
|------|---------|--------|
| `task-status-open-queue` | Task status → `open` with `pipeline_template` set | Sets `pipeline_status=queued`, daemon picks up |
| `task-status-active-launch` | Task status → `active` with `pipeline_template` set | Launches pipeline immediately, bypasses concurrency |
| `pipeline-stage-rewind` | Pipeline `pending_action`/`stage` changed | Calls `pipeline_rewind.rewind_to_stage()` |
| `pipeline-reset-phase` | Pipeline `reset` set to `true` | Calls `pipeline_rewind.reset_current_phase()`, clears flag |
| `pipeline-phase-rewind` | Pipeline `current_phase`/`phase` set to lower number | Calls `pipeline_rewind.rewind_to_phase()` |

**Key types**:
```python
EditContext(coord, prefix, slug, filepath, field_key, old_value, new_value, all_fields, dry_run)
HookResult(action, f_label_suffix, cascades)
```

**Integration point**: `codex_engine.py` line ~2770, after F-label push in `execute_edit()`.

### `scripts/pipeline_rewind.py`
**Purpose**: Rewind pipelines to earlier stages/phases via field changes.

**3 public functions**:
```python
rewind_to_stage(version, target_stage, dry_run=False) -> dict
rewind_to_phase(version, target_phase, dry_run=False) -> dict
reset_current_phase(version, dry_run=False) -> dict
```

All operations:
1. Validate target using `template_parser` stage ordering
2. Mark later stages as `rewound` in `_state.json` (audit trail preserved)
3. Set `pending_action` to target, clear `dispatch_claimed`
4. Write-through to `.md` frontmatter

**CLI**: `python3 scripts/pipeline_rewind.py <version> --stage <stage> [--dry-run]`

### `scripts/persona_loader.py`
**Purpose**: Dynamic persona config from `.md` files, replacing hardcoded `PERSONA_CONFIGS`.

**Functions**:
```python
load_persona_config(persona, template_name=None) -> dict[str, str]
# Returns: {prefix: 'full'|'summary'|'tree'}

load_persona_access(persona) -> set[int]
# Returns: set of allowed e-mode numbers (e.g., {0, 1, 2})
```

**Resolution order**: template `persona_overrides` → persona `.md` `render_config` → fallback defaults.

**Caching**: mtime-based. Re-reads file only when modified.

### `scripts/command_registry.py`
**Purpose**: Cross-surface command registration. Any command can appear as e-mode op, slash command, CLI command, or skill.

**Auto-discovery**: Scans `scripts/` for `COMMAND_META` dicts (AST-parsed), `skills/` for `SKILL.md` files.

**Script skeleton** (created by `e2 sc`):
```python
COMMAND_META = {
    "name": "my-tool",
    "surfaces": ["cli", "e0"],
    "persona_access": ["*"],
    "description": "...",
    "args": ["arg1"],
}
```

**Singleton**: `from command_registry import registry`

### `scripts/reactive_daemon.py`
**Purpose**: Polls `tasks/` and `pipelines/` for frontmatter changes every 30 seconds. Manages queued task launches with configurable spacing.

**Core loop**:
1. `detect_changes()` — mtime scan (~1ms for 120+ files)
2. `handle_change()` — diff frontmatter, fire reactive handlers
3. `check_queued_launches()` — launch queued tasks respecting concurrency + cadence

**Config**: Reads `state/orchestration_config.json` every tick (written by `e0 cadence`).

**Deployment**:
```bash
# Systemd (production)
cp docker/openclaw-reactive.service ~/.config/systemd/user/
systemctl --user enable --now openclaw-reactive

# Manual
python3 scripts/reactive_daemon.py --loop --interval 30 --queue-spacing 1h

# One-shot (cron)
python3 scripts/reactive_daemon.py --once
```

**Portability**: Uses `%h` systemd specifier and `OPENCLAW_WORKSPACE` env var.

### `scripts/migrate_task_schema_v2.py`
**Purpose**: One-time migration adding 4 new fields to all task `.md` files.

### `scripts/migrate_pipeline_frontmatter.py`
**Purpose**: One-time migration adding reactive fields to all pipeline `.md` files.

### `docker/openclaw-reactive.service`
**Purpose**: Systemd unit for the reactive daemon. Uses `%h` for home dir portability.

---

## Modified Files

### `scripts/codex_engine.py` (Core Engine)

**Changes by area**:

| Area | Line Range | Change |
|------|-----------|--------|
| Task schema | ~2093 | Added `'f': 'file', 'sc': 'script'` to `PREFIX_TO_CREATE_TYPE` |
| Valid statuses | ~2099 | Added `'queued', 'done', 'in-progress'` to `TASK_VALID_STATUSES` |
| Persona system | ~1225 | Replaced `PERSONA_CONFIGS` dict with dynamic `persona_loader` import |
| Persona render | ~1285 | `persona_cfg = _load_persona_config(persona)` instead of dict lookup |
| Persona validation | ~5398 | Uses `KNOWN_PERSONAS` set, allows dynamic discovery |
| Mode gating | ~5158 | Added persona access check at top of `_dispatch_v2_operation_inner()` |
| Post-edit hooks | ~2770 | Added hook firing after F-label push in `execute_edit()` |
| Operations enrichment | ~2685 | Added `prefix` and `slug` to operations dicts |
| E0 op index | ~3958 | Added ops 10 (kill), 11 (restart), 12 (cadence) |
| E0 cadence | ~4718 | New cadence handler before orch engine check |
| E0 parser | ~4665 | Added `'cadence'` to standalone word recognition |
| Enum fields | ~3967 | Added `launch_mode` and `pipeline_status` enum maps |
| E2 script/file | ~2878 | `sc` prefix creates COMMAND_META script, `f` creates blank file |
| E1 @path | ~2424 | `@path` syntax for raw file editing |
| E3 hook | ~4444 | New `e3 hook` subcommand for hook scaffolding |
| E3 discover | ~4498 | New `e3 discover` for command index rebuild |
| E3 category | ~4330 | Auto-creates `.namespace` marker on new category |
| Dashboard | ~5360 | New `_render_dashboard()` function |
| Dashboard route | ~5530 | `dashboard`/`cockpit` subcommand in `main()` |

### `scripts/pipeline_update.py`

| Function | Change |
|----------|--------|
| `load_state()` | Now reads `.md` frontmatter first, merges with JSON. `.md` wins for `status`, `pending_action`, `dispatch_claimed`, `last_updated`, `current_phase`. Logs drift warnings. |
| `save_state()` | Added write-through: updates `.md` frontmatter after writing JSON. |
| New: `_parse_pipeline_md_frontmatter()` | Parses pipeline `.md` YAML frontmatter. |
| New: `_update_pipeline_md_frontmatter()` | Writes specific fields to `.md` preserving body. |

### `scripts/orchestration_engine.py`

| Function | Change |
|----------|--------|
| `load_state_json()` (fallback) | Now reads `.md` frontmatter and merges as authoritative for shared fields. |

### `scripts/template_parser.py`

4 new helper functions added before `clear_cache()`:

```python
get_stage_order(template_name) -> list[str]        # flat ordered stage list
get_phase_first_stage(template_name, phase) -> str  # first stage of phase N
stage_phase(template_name, stage) -> int            # which phase a stage belongs to
get_phase_stages(template_name, phase) -> list[str] # all stages in phase N
```

Also fixed pre-existing bug in `__main__` block: block_transitions unpacking (3-tuple vs 4-tuple).

### `schemas/task.md`

4 new fields added to task schema:

```yaml
pipeline_template:    # slug of template to use (e.g., builder-first, research)
current_stage:        # current pipeline stage (normally derived, writable for override)
pipeline_status:      # lifecycle status (queued, launching, in_pipeline, stalled, complete)
launch_mode:          # queued (respects concurrency) or active (bypasses)
```

Status enum expanded: `[open, active, in_pipeline, in-progress, blocked, queued, done]`

### `personas/architect.md`, `builder.md`, `critic.md`

New frontmatter fields:

```yaml
render_config:
  full: [d, k, t, p, s, w]   # namespaces shown in full
  summary: [l]                 # namespaces shown as summary count
  tree: [p]                    # namespaces shown as directory tree (builder only)
mode_access: [0, 1, 2]        # allowed e-mode numbers
```

### `modes/orchestrate.md`

Added op 12 to `operation_index`: `12: cadence`

---

## New E-Mode Operations

### `e0 cadence [interval]`
Set or show the queue launch spacing.

```
e0 cadence           — show current setting
e0 cadence 1h        — space launches 1 hour apart
e0 cadence 30m       — 30 minutes apart
e0 cadence 0         — immediate (no spacing)
```

Persists to `state/orchestration_config.json`. Daemon reads every tick without restart.

### `e2 sc "name"`
Create a Python script with `COMMAND_META` skeleton for auto-discovery.

```
e2 sc "my-pipeline-tool"
→ creates scripts/my-pipeline-tool.py with COMMAND_META dict
```

### `e2 f "path"`
Create a blank file at any workspace-relative path.

```
e2 f "data/config.yaml"
→ creates data/config.yaml (empty)
```

### `e1 @path B+ "text"`
Edit any file by path (not just primitives).

```
e1 @scripts/foo.py B+ "# new code"
e1 @data/config.yaml B "full replacement"
```

### `e3 hook <name> [surfaces...]`
Scaffold a new hook with HOOK.md + handler.ts + command registry integration.

```
e3 hook my-hook cli slash e0
→ creates hooks/my-hook/HOOK.md + handler.ts
→ registers in command_index.json
```

### `e3 discover`
Rebuild the command index from all scripts, skills, and hooks.

```
e3 discover
→ scans scripts/ for COMMAND_META, skills/ for SKILL.md, hooks/ for HOOK.md
→ writes state/command_index.json
```

### `R dashboard` / `R cockpit`
Combined TUI status view showing active pipelines, queued tasks, cadence, and recent events.

```
R dashboard [--as persona] [--watch]
```

---

## Reactive Pipeline Lifecycle

### Queued Launch Flow
```
e1t5 pipeline_template builder-first    # set template
e1t5 status open                        # hook sets pipeline_status=queued
                                        # daemon detects queue, waits for slot + cadence
                                        # daemon launches pipeline when eligible
```

### Active (Immediate) Launch Flow
```
e1t5 pipeline_template research
e1t5 status active                      # hook launches immediately, bypasses concurrency
```

### Pipeline Rewind
```
e1p3 pending_action p1_builder_implement  # rewind to specific stage
e1p3 current_phase 1                      # rewind to phase 1 start
e1p3 reset true                           # reset current phase (flag auto-clears)
```

### External Change Detection
When `.md` files are edited outside of e1 (vim, scripts, etc.), the reactive daemon detects the mtime change within 30 seconds and fires the same reactive handlers.

---

## Persona Mode Gating

Personas now have `mode_access` controlling which e-modes they can use:

| Persona | Allowed Modes | Blocked |
|---------|--------------|---------|
| architect | e0, e1, e2 | e3 |
| builder | e0, e1, e2, e3 | none |
| critic | e0, e1 | e2, e3 |

When a restricted persona hits a blocked mode, the system prints an error. This is enforced in `_dispatch_v2_operation_inner()`.

---

## .md Source of Truth

### Authoritative Fields (in pipeline .md)
These fields in `.md` frontmatter override `_state.json` when they differ:

- `status`
- `pending_action`
- `dispatch_claimed`
- `last_updated`
- `current_phase`

### Write-Through
When `save_state()` writes `_state.json`, it also updates these fields in the pipeline `.md` frontmatter.

### Drift Detection
When `load_state()` detects a mismatch between `.md` and JSON, it logs a warning and uses `.md` value.

---

## State Files

| File | Purpose | Written By |
|------|---------|-----------|
| `state/orchestration_config.json` | Queue cadence, updated_by | `e0 cadence` |
| `state/daemon_state.json` | Daemon snapshots, last_launch_at, tick_count | `reactive_daemon.py` |
| `state/command_index.json` | Discovered commands for cockpit rendering | `e3 discover` |

---

## Portability

All new code uses `WORKSPACE = Path(__file__).resolve().parent.parent` for path resolution. No hardcoded `/home/ubuntu` paths in new files.

**systemd service**: Uses `%h` specifier for home directory. Set `OPENCLAW_WORKSPACE` env var if workspace is non-standard.

**To bring up on a new machine**:
1. Clone belam-codex repo
2. Ensure Python 3.10+ with PyYAML
3. Run `python3 scripts/migrate_task_schema_v2.py` (idempotent, skips already-migrated)
4. Run `python3 scripts/migrate_pipeline_frontmatter.py` (idempotent)
5. Optionally install systemd service: `cp docker/openclaw-reactive.service ~/.config/systemd/user/`
6. Run `python3 scripts/codex_engine.py e3 discover` to build command index

---

## File Inventory

### New Files (10)
```
scripts/post_edit_hooks.py           (~300 lines)  Hook registry + 5 reactive hooks
scripts/pipeline_rewind.py           (~200 lines)  Stage/phase/reset rewind engine
scripts/persona_loader.py            (~150 lines)  Dynamic persona config from .md
scripts/command_registry.py          (~300 lines)  Cross-surface command registration
scripts/reactive_daemon.py           (~400 lines)  mtime-based change detection daemon
scripts/migrate_task_schema_v2.py    (~100 lines)  One-time task schema migration
scripts/migrate_pipeline_frontmatter.py (~100 lines)  One-time pipeline migration
docker/openclaw-reactive.service     (~15 lines)   Systemd unit for daemon
```

### Modified Files (11)
```
scripts/codex_engine.py              Hooks, personas, dashboard, e-mode expansions
scripts/pipeline_update.py           .md-first load/save with write-through
scripts/orchestration_engine.py      .md-first load_state_json
scripts/template_parser.py           Stage ordering helpers + bugfix
schemas/task.md                      4 new fields
personas/architect.md                render_config, mode_access
personas/builder.md                  render_config, mode_access
personas/critic.md                   render_config, mode_access
modes/orchestrate.md                 Op 12 (cadence)
```

### Migrated Data
```
75 task .md files                    Added pipeline_template, current_stage, pipeline_status, launch_mode
41 pipeline .md files                Added pending_action, current_phase, dispatch_claimed, last_updated, reset
```
