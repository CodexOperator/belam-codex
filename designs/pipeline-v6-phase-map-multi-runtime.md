# Pipeline V6: Phase Map + Multi-Runtime Dispatch

**Status:** Design  
**Author:** Belam  
**Date:** 2026-04-19  
**Related:** d95 (phase-n-generic-pipeline-template-architecture), d54 (orchestration-fire-and-forget-dispatch)

---

## Problem Statement

The current pipeline system has two limitations:

1. **Template-locked phase structure:** Once a pipeline is created from a template (e.g. `builder-first`, `research`), the phase/stage sequence is fixed. You can't add, remove, reorder, or modify stages per-pipeline without creating a new template.

2. **Single dispatch target:** All stages dispatch to OpenClaw agents via `openclaw agent --agent <role> --message <msg>`. There's no way to route a stage to Claude Code (`claude` CLI), Codex CLI (`codex`), or other coding agent runtimes — even though these tools are installed and have native advantages (GitNexus, Cavekit, file-level autonomy).

## Design

### 1. `phase_map` — Per-Pipeline Customizable Phase Structure

When a pipeline is created from a template, the template's `phases:` YAML is **copied into the pipeline's frontmatter** as a `phase_map` field. This is the pipeline's **local, mutable copy** of the phase structure.

#### Schema

```yaml
# Pipeline frontmatter (pipelines/<version>.md)
---
primitive: pipeline
status: pipeline_created
priority: high
type: builder-first
version: my-feature-v1
pipeline_template: builder-first   # source template (for reference/lineage)
phase_map:
  1:
    label: "Autonomous Build"
    repeating: false
    gate: human
    stages:
      - role: builder
        action: implement
        session: fresh
        runtime: claude-code         # ← NEW: dispatch target override
      - role: builder
        action: bugfix
        session: continue
        runtime: claude-code
      - role: critic
        action: review
        session: fresh
        runtime: openclaw            # default — explicit for clarity
  2:
    label: "Architect-Led Refinement"
    repeating: false
    gate: human
    stages:
      - role: architect
        action: design
        session: fresh
        runtime: openclaw
      - role: builder
        action: implement
        session: fresh
        runtime: codex
      - role: builder
        action: bugfix
        session: continue
        runtime: codex
      - role: critic
        action: review
        session: fresh
        runtime: openclaw
  3:
    label: "Iteration"
    repeating: true                  # ← can loop back to phase 3 start
    gate: human
    stages:
      - role: architect
        action: design
        session: fresh
        runtime: openclaw
      - role: builder
        action: implement
        session: fresh
        runtime: claude-code
      - role: critic
        action: review
        session: fresh
        runtime: openclaw
block_routing:
  critic:
    review: { agent: builder, session: continue }
auto_complete_on_clean_pass: false
complete_task_agent: architect
---
```

#### Behavior

- **On pipeline creation:** `launch_pipeline.py` reads the template, copies `phases:` → `phase_map:` in the pipeline's frontmatter. Block routing, auto-complete, and complete_task_agent are also copied.
- **After creation:** The `phase_map` is the single source of truth for this pipeline's structure. Template changes don't affect existing pipelines.
- **Editing:** `e1p{n} phase_map.1.gate auto` or direct frontmatter edit. Codex Engine field access via dot-path.
- **Stage names are generated from phase_map:** `p{phase}_{role}_{action}` — same as today.
- **Template parser fallback:** If `phase_map` is absent in frontmatter (legacy pipelines), fall back to template lookup — full backward compat.

#### New Fields per Stage

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `role` | string | required | Agent role (architect, critic, builder, system) |
| `action` | string | required | Stage action (implement, review, design, etc.) |
| `session` | string | `fresh` | Session mode: `fresh` or `continue` |
| `runtime` | string | `openclaw` | Dispatch target (see §2) |
| `timeout` | int | from roster | Override timeout for this specific stage (seconds) |
| `model` | string | from roster | Override model for this stage |
| `workdir` | string | workspace | Working directory for CLI runtimes |
| `flags` | string | `""` | Extra CLI flags (e.g. `--yolo`, `--dangerously-skip-permissions`) |

#### New Fields per Phase

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `label` | string | `"Phase {n}"` | Human-readable phase label |
| `repeating` | bool | `false` | Whether this phase can loop (human decides at gate) |
| `gate` | string | `human` | Gate type: `human`, `auto`, `critic-pass` |

### 2. Multi-Runtime Dispatch

#### Supported Runtimes

| Runtime | CLI Command | Permissions Mode | Session Type |
|---------|-------------|------------------|--------------|
| `openclaw` | `openclaw agent --agent {role} --message {task}` | N/A (managed by OpenClaw) | OpenClaw agent session |
| `claude-code` | `claude --dangerously-skip-permissions --print {task}` | Full auto (no stalls) | Subprocess (Popen) |
| `codex` | `codex --yolo exec {task}` | Full auto (no stalls) | Subprocess (Popen, PTY) |
| `acp` | `sessions_spawn(runtime="acp", agentId=...)` | Via ACP | Only from agent turns (not scripts) |

> **Note on `acp` runtime:** This is only usable when dispatch originates from an LLM agent turn (e.g. Belam dispatching during a heartbeat). Script-level dispatch (`fire_and_forget_dispatch`, `auto_wiggum`) cannot call `sessions_spawn` — it's an LLM tool, not a CLI command. For script-level dispatch, use `claude-code` or `codex` runtimes.

#### Dispatch Flow

```
fire_and_forget_dispatch(version, stage, agent)
  │
  ├── Read phase_map from pipeline frontmatter
  │   └── (fallback: read from template if no phase_map)
  │
  ├── Resolve runtime for this stage
  │   └── stage.runtime || phase default || "openclaw"
  │
  ├── runtime == "openclaw"
  │   └── subprocess.Popen(['openclaw', 'agent', '--agent', role, '--message', task])
  │       (existing behavior, unchanged)
  │
  ├── runtime == "claude-code"
  │   └── subprocess.Popen(
  │         ['claude', '--dangerously-skip-permissions', '--print', task],
  │         cwd=workdir,
  │         stdout=log_file, stderr=subprocess.STDOUT,
  │         start_new_session=True
  │       )
  │
  └── runtime == "codex"
      └── subprocess.Popen(
            ['codex', '--yolo', 'exec', task],
            cwd=workdir,
            stdout=log_file, stderr=subprocess.STDOUT,
            start_new_session=True,
            # Note: codex needs PTY — may need script(1) wrapper or pty.spawn
          )
```

#### Context Injection Differences

| Runtime | Context Method | Pipeline State | Memory |
|---------|---------------|----------------|--------|
| `openclaw` | Pipeline-context plugin injects into system prompt | Automatic | Agent memory files |
| `claude-code` | Baked into task prompt + CLAUDE.md in workdir | Task prompt includes full pipeline state | Task prompt includes relevant memory excerpts |
| `codex` | Baked into task prompt + AGENTS.md in workdir | Task prompt includes full pipeline state | Task prompt includes relevant memory excerpts |

For `claude-code` and `codex` runtimes, the dispatch function must build a **self-contained task prompt** that includes:
1. Pipeline version, current stage, phase context
2. Files to read/modify (from `_files_for_stage()`)
3. Completion instructions (what to output/commit when done)
4. Accumulated notes from previous stages
5. Success criteria

#### Completion Detection

| Runtime | How Completion is Detected | How to Signal Stage Done |
|---------|---------------------------|------------------------|
| `openclaw` | Agent-end telemetry plugin + `check_completions()` | Agent calls `pipeline_orchestrate.py complete` |
| `claude-code` | Process exit (PID monitoring via `auto_wiggum` pattern) | Write completion marker file OR call `pipeline_orchestrate.py complete` at end of task |
| `codex` | Process exit (PID monitoring) | Same as claude-code |

**Completion marker pattern** (for CLI runtimes that can't easily call orchestrate):
```bash
# At end of task, the CLI agent writes:
echo '{"status": "complete", "notes": "summary", "learnings": "insights"}' > \
  /tmp/pipeline_complete_{version}_{stage}.json
```

A **completion watcher** (lightweight loop in `auto_wiggum` or a new `completion_monitor.py`) polls for:
1. Process exit (PID gone)  
2. Completion marker file exists  
3. Then calls `pipeline_orchestrate.py <version> complete <stage> --agent <role> --notes "from marker"`

### 3. Template → Pipeline Lifecycle

```
Template (templates/builder-first-pipeline.md)
  │
  ├── phases: { 1: {...}, 2: {...}, 3: {...} }     # Template definition
  │
  └── launch_pipeline.py --template builder-first
      │
      ├── Copy phases → phase_map in pipeline frontmatter
      ├── Copy block_routing, auto_complete, complete_task_agent
      ├── User can now edit phase_map freely
      │
      └── Pipeline runs using its LOCAL phase_map
          (template is never consulted again for this pipeline)
```

#### Template Parser Changes

`template_parser.py` needs a new entry point:

```python
def parse_phase_map(phase_map: dict) -> dict:
    """Parse a pipeline's local phase_map (same format as template phases).
    
    Returns the same shape as parse_template():
      transitions, block_transitions, status_bumps, start_status_bumps, 
      human_gates, pipeline_fields
    """
    # Reuse _parse_phase_based() with the phase_map dict
    # Add runtime field preservation in the output
```

`orchestration_engine.py` changes:

```python
def resolve_transition(version, stage):
    # 1. Try pipeline's phase_map first
    phase_map = _load_phase_map(version)  # from pipeline frontmatter
    if phase_map:
        parsed = parse_phase_map(phase_map)
        ...
    # 2. Fallback to template
    else:
        template = _resolve_template_name(...)
        parsed = parse_template(template)
        ...
```

### 4. Runtime Config in `auto_wiggum`

`auto_wiggum.py` needs a `--runtime` flag:

```bash
# OpenClaw agent (existing)
python3 scripts/auto_wiggum.py --agent builder --timeout 900 --runtime openclaw \
  --pipeline my-v1 --stage p1_builder_implement --task "..."

# Claude Code
python3 scripts/auto_wiggum.py --agent builder --timeout 900 --runtime claude-code \
  --pipeline my-v1 --stage p1_builder_implement --task "..." \
  --workdir ~/repos/my-project

# Codex
python3 scripts/auto_wiggum.py --agent builder --timeout 900 --runtime codex \
  --pipeline my-v1 --stage p1_builder_implement --task "..." \
  --workdir ~/repos/my-project
```

The steer timer logic stays the same — at 80% timeout, send a "wrap up" signal:
- **openclaw:** `openclaw agent --agent builder --message "STEER: wrap up"`
- **claude-code:** Write to stdin or send SIGTERM + let `--print` mode flush
- **codex:** Send keys via PTY or write to stdin

### 5. Codex Engine Integration

#### Viewing Phase Map
```
p3                          # Shows pipeline p3 including its phase_map
e1p3 phase_map.2.gate auto  # Change phase 2 gate to auto
e1p3 phase_map.1.stages.0.runtime claude-code  # Set stage runtime
```

#### New Fields in Pipeline View
```
╶─ p3   my-feature-v1  p1_active/high  [claude-code dispatched 2h ago]
│  ╶─ phase_map: 3 phases (2 human-gated, 1 auto)
│  ╶─ current: p1_builder_implement (claude-code)
```

### 6. Implementation Plan

#### Phase 1: phase_map in Frontmatter (No Runtime Changes Yet)

1. Modify `launch_pipeline.py` to copy template phases → `phase_map` in frontmatter
2. Modify `template_parser.py` to add `parse_phase_map()` 
3. Modify `orchestration_engine.py` → `resolve_transition()` to check phase_map first
4. Modify `pipeline_update.py` to use phase_map when present
5. Backward compat: pipelines without phase_map still use template lookup
6. Test: create pipeline, edit phase_map, verify stages resolve correctly

#### Phase 2: Multi-Runtime Dispatch

7. Add `runtime` field support in `_parse_phase_based()`
8. Modify `fire_and_forget_dispatch()` to branch on runtime
9. Build CLI-runtime dispatch functions: `_dispatch_claude_code()`, `_dispatch_codex()`
10. Build self-contained task prompt generator for CLI runtimes
11. Build completion marker watcher in `auto_wiggum.py` (or new script)
12. Add `--runtime` flag to `auto_wiggum.py`
13. Test: run a stage with `runtime: claude-code`, verify completion detection

#### Phase 3: Codex Engine + Dashboard

14. Add `phase_map` rendering to pipeline view in codex_engine.py
15. Add dot-path editing for phase_map fields via `e1`
16. Update pipeline dashboard to show runtime per stage
17. Update Telegram notifications to include runtime info

### 7. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| phase_map lives in frontmatter | Yes | Single file = single source of truth, editable, git-tracked |
| Template copied at creation, never re-read | Yes | Prevents template changes from breaking running pipelines |
| CLI runtimes use `--dangerously-skip-permissions` / `--yolo` | Yes | Autonomous pipeline stages must not stall on permission prompts |
| Completion via marker file + PID monitoring | Yes | CLI processes can't call back to OpenClaw tools; marker files are simple and reliable |
| `acp` runtime only from agent turns | Yes | `sessions_spawn` is an LLM tool, not available in Python scripts |
| `phase_map` is optional (backward compat) | Yes | Existing pipelines without phase_map continue to work via template fallback |
| Repeating phases loop at human gate | Yes | Human decides "repeat phase 3" or "advance/complete" |
| Runtime default is `openclaw` | Yes | Zero disruption to existing pipelines |

### 8. Open Questions

1. **Codex PTY requirement:** `codex --yolo` may need a real PTY. Options: `script -c` wrapper, Python `pty.spawn()`, or `expect`. Need to test which works with Popen.

2. **Claude Code output capture:** `--print` mode outputs to stdout. Should we capture this to a log file for post-stage review, or let it go to /dev/null?
   - **Recommendation:** Capture to `logs/pipeline_{version}_{stage}.log`

3. **Workdir per stage:** Should `workdir` be per-stage or per-pipeline? Different stages might need different repos.
   - **Recommendation:** Per-stage in phase_map, with pipeline-level default.

4. **CLAUDE.md injection:** Should we write a temporary `CLAUDE.md` in the workdir with pipeline context before dispatching Claude Code? This would give it Cavekit-native context.
   - **Recommendation:** Yes — write `.claude/settings.json` + `CLAUDE.md` with pipeline state before dispatch, clean up after.

5. **Steer mechanism for CLI runtimes:** Claude Code `--print` mode doesn't have an interactive channel. Steer messages may need to be via SIGTERM + restart with "continue from where you left off" prompt.
   - **Recommendation:** For V1, just use hard timeout + restart. Steer is nice-to-have.

---

## File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `scripts/launch_pipeline.py` | Modify | Copy template phases → phase_map in frontmatter |
| `scripts/template_parser.py` | Modify | Add `parse_phase_map()`, preserve `runtime` field |
| `scripts/orchestration_engine.py` | Modify | `resolve_transition()` checks phase_map first; runtime-aware dispatch |
| `scripts/pipeline_update.py` | Modify | Use phase_map when present for transitions |
| `scripts/auto_wiggum.py` | Modify | Add `--runtime` flag, CLI dispatch modes |
| `scripts/completion_monitor.py` | New | Watch for completion markers + PID exit |
| `scripts/codex_engine.py` | Modify | Render phase_map in pipeline view, dot-path editing |
| `scripts/pipeline_dashboard.py` | Modify | Show runtime per stage in dashboard |
| `templates/*.md` | No change | Templates unchanged, phase_map is a copy |
