# CLI-Agnostic Orchestration + Shared Cockpit Design Plan

> For Hermes: planning only. No code changes in this pass.

Goal: refactor belam-codex orchestration so templates define phase/stage topology while CLI launch behavior is selected through a registry of adapters, with task-frontmatter overrides controlling per-phase and per-stage runtime selection.

Architecture:
- Split orchestration into two layers: topology layer and execution layer.
- Topology layer answers: what phase/stage comes next, does it human-gate, does phase repeat, which default CLI should run this stage.
- Execution layer answers: how to launch a chosen CLI, with which args, with popen or tmux, how to resume, and how to surface questions back to main session / Telegram.
- Initial implementation should prefer simple `subprocess.Popen` launchers, while keeping a clean path to a later shared-tmux cockpit backend.

Tech stack:
- Python existing scripts in `scripts/`
- Markdown/YAML frontmatter in `tasks/`, `pipelines/`, `templates/`
- Existing CLI tools present on system: `codex`, `claude`, `openclaw`, `tmux`
- Existing cockpit pieces: `bin/R`, `scripts/codex_panes.py`, `scripts/pipeline_dashboard.py`, `scripts/codex_stream.py`

---

## Current Context

Observed state from repo inspection:
- `scripts/orchestration_engine.py` already parses template runtime metadata and builds structured dispatch payloads.
- Real dispatch still routes through `fire_and_forget_dispatch()` -> `subprocess.Popen([... 'openclaw', 'agent', ...])`.
- Templates currently mix topology and runtime metadata under `runtime:`.
- `bin/R monitor` and `scripts/codex_panes.py` already prove shared tmux cockpit patterns exist.
- User direction for this design:
  - keep orchestration CLI-agnostic
  - maintain a list/database of CLIs and launch recipes
  - templates define phase/stage maps only
  - tasks store template path and per-phase/per-stage overrides in frontmatter
  - Codex should default `--yolo`
  - Claude should default dangerous skip-permissions equivalent
  - workers must be able to ask questions back through main session and/or Telegram relay
  - initial implementation may use popen first if simpler than tmux
  - shared cockpit preferred over per-role cockpit for first tmux phase

## Design Principles

1. Templates define workflow topology, not launch internals.
2. Task frontmatter is authoritative for runtime overrides.
3. CLI launchers are adapters in a registry, not hardcoded branches spread across orchestrator.
4. Popen-first implementation; tmux backend second.
5. Shared cockpit session per pipeline when tmux lands.
6. Human-question relay is first-class, not a hack.
7. Existing state machine and handoff logic should be preserved where possible.

---

## Proposed Data Model

### 1) CLI Registry

Add a machine-readable registry file:
- Create: `state/cli_registry.json`

Purpose:
- canonical source for installed CLIs and launch recipes
- decouple orchestration from specific programs

Suggested shape:

```json
{
  "codex": {
    "label": "OpenAI Codex CLI",
    "program": "codex",
    "default_args": ["--yolo"],
    "launch_mode": "popen",
    "supports_tmux": true,
    "supports_resume": true,
    "question_strategy": "packet_and_relay",
    "task_entry": "file"
  },
  "claude": {
    "label": "Claude Code",
    "program": "claude",
    "default_args": ["--dangerously-skip-permissions"],
    "launch_mode": "popen",
    "supports_tmux": true,
    "supports_resume": true,
    "question_strategy": "packet_and_relay",
    "task_entry": "file"
  },
  "openclaw": {
    "label": "OpenClaw Agent CLI",
    "program": "openclaw",
    "default_args": ["agent"],
    "launch_mode": "popen",
    "supports_tmux": false,
    "supports_resume": true,
    "question_strategy": "native_session",
    "task_entry": "message"
  }
}
```

Notes:
- Keep this file declarative.
- Runtime discovery script can later validate installed CLIs and annotate availability.

### 2) Template Topology Format

Move templates toward topology-only structure.

Current templates mix `runtime:` with stage maps. New target should make `path` authoritative.

Suggested template YAML block:

```yaml
first_agent: architect
type: research
path:
  phase_1:
    repeat: once
    human_gate: false
    stages:
      - key: p1_architect_design
        role: architect
        action: design
        cli: architect_default
      - key: p1_critic_design_review
        role: critic
        action: design_review
        cli: critic_default
  phase_2:
    repeat: several
    human_gate: true
    stages:
      - key: p2_builder_analysis_scripts
        role: builder
        action: analysis_scripts
        cli: builder_default
```

Meaning:
- `repeat`: `once | several | indefinite`
- `human_gate`: phase-level gate declaration
- `cli`: symbolic reference, not executable details

Important:
- preserve compatibility parser for old templates during migration
- parser should normalize old and new formats into one internal structure

### 3) Task Frontmatter Overrides

Task frontmatter becomes runtime authority.

Extend `schemas/task.md` and task files with fields like:

```yaml
pipeline_template: research
pipeline_template_path: templates/research-pipeline.md
pipeline_runtime:
  defaults:
    cockpit_mode: shared
    launcher: popen
  cli_aliases:
    architect_default: claude
    builder_default: codex
    critic_default: claude
  phase_overrides:
    phase_2:
      repeat: several
      human_gate: true
      launcher: popen
  stage_overrides:
    p2_builder_analysis_scripts:
      cli: codex
      args: ["--yolo"]
    p2_critic_analysis_code_review:
      cli: claude
      args: ["--dangerously-skip-permissions"]
      ask_on_question: main_session
```
```

Resolution order:
1. stage override on task
2. phase override on task
3. task defaults
4. template symbolic cli reference
5. global registry defaults

### 4) Pipeline Materialization

When a task launches a pipeline, materialize resolved runtime into pipeline state/frontmatter.

Suggested pipeline additions:
- `source_task:`
- `template_path:`
- `resolved_cli_map:` optional pointer/file path
- `cockpit_session:` optional shared session name

Keep runtime snapshot in state JSON too for audit/replay.

---

## Proposed Code Architecture

### A. New module: CLI registry loader
- Create: `scripts/cli_registry.py`

Responsibilities:
- load `state/cli_registry.json`
- validate requested cli keys
- merge default args with overrides
- expose `resolve_cli_spec(cli_name)`

### B. New module: dispatch adapters
- Create: `scripts/dispatch_adapters.py`

Core interface:

```python
class DispatchAdapter:
    def build_command(self, payload, cli_spec, runtime): ...
    def launch_popen(self, command, cwd, log_path): ...
    def launch_tmux(self, session_name, command, cwd): ...
    def relay_question(self, question_packet): ...
```

First adapters:
- `CodexAdapter`
- `ClaudeAdapter`
- `OpenClawAdapter`

### C. New module: runtime resolution
- Create: `scripts/runtime_resolution.py`

Responsibilities:
- resolve template path + topology
- resolve task phase/stage overrides
- map symbolic `cli` refs to concrete CLI registry entries
- choose `launcher` = `popen` initially, `tmux` later where requested

### D. Refactor orchestration engine
- Modify: `scripts/orchestration_engine.py`

Refactor target:
- preserve transition logic
- preserve handoff/state machine behavior
- replace direct `openclaw` launch in `fire_and_forget_dispatch()` with:
  1. build payload
  2. resolve runtime
  3. write task packet
  4. dispatch through adapter

Suggested new functions:
- `resolve_stage_runtime(version, stage, agent) -> dict`
- `write_dispatch_packet(version, stage, agent, payload) -> Path`
- `dispatch_via_adapter(payload, runtime) -> dict`
- `dispatch_via_popen(...)`
- `dispatch_via_tmux(...)` (stub first, real later)

### E. Question relay path
- Create: `scripts/agent_questions.py`

Purpose:
- worker CLIs write question packets to workspace
- main session / Telegram relay consumes them

Suggested packet dir:
- `pipeline_builds/<version>/questions/`

Packet shape:

```json
{
  "pipeline": "foo",
  "stage": "p2_builder_analysis_scripts",
  "agent": "builder",
  "cli": "codex",
  "question": "Need API key or mock path?",
  "relay": "main_session",
  "created_at": "..."
}
```

Phase 1 behavior:
- simple file drop + orchestrator poll
- relay destination options:
  - `main_session`
  - `telegram`
  - `both`

### F. Shared cockpit backend
- Later create/extend shared tmux backend around existing pieces
- Likely modify: `bin/R`, `scripts/codex_panes.py`

Shared session target:
- one tmux session per pipeline
- panes can show:
  - dashboard
  - stream/diff
  - current worker log
  - optional question queue

For first implementation, keep this behind a clean interface and do not block popen rollout on it.

---

## File Plan

### Likely new files
- `scripts/cli_registry.py`
- `scripts/dispatch_adapters.py`
- `scripts/runtime_resolution.py`
- `scripts/agent_questions.py`
- `state/cli_registry.json`
- `docs/cli-orchestration.md` or keep design in handoff docs only

### Likely modified files
- `scripts/orchestration_engine.py`
- `scripts/template_parser.py`
- `scripts/launch_pipeline.py`
- `scripts/pipeline_orchestrate.py`
- `schemas/task.md`
- `templates/research-pipeline.md`
- `templates/builder-first-pipeline.md`
- `templates/builder-first-autogate-pipeline.md`
- `bin/R` (later shared cockpit attach/status helpers)

### Likely tests
- `scripts/tests/test_template_parser.py`
- new: `scripts/tests/test_cli_registry.py`
- new: `scripts/tests/test_runtime_resolution.py`
- new: `scripts/tests/test_dispatch_adapters.py`
- new: `scripts/tests/test_question_relay.py`

---

## Step-by-Step Implementation Plan

### Phase A — schema and parsing
1. Extend template parser to support a `path` model with phase metadata and stage CLI references.
2. Keep backward compatibility with existing `runtime:` templates.
3. Extend task schema for `pipeline_template_path` and `pipeline_runtime` overrides.
4. Update pipeline launch logic to materialize task runtime into created pipeline state.

Validation:
- parse old templates unchanged
- parse new path-style template
- resolve task frontmatter overrides deterministically

### Phase B — registry and adapter abstraction
5. Add `state/cli_registry.json` and registry loader.
6. Add dispatch adapter interface and concrete Codex/Claude/OpenClaw adapters.
7. Refactor orchestration engine dispatch to use adapter resolution instead of direct `openclaw` launch.

Validation:
- given stage runtime -> resolved command matches expected CLI + args
- codex gets `--yolo` by default
- claude gets dangerous-skip-permissions default
- override args merge correctly

### Phase C — dispatch packets and question relay
8. Materialize per-stage dispatch packets under pipeline build dir.
9. Add question packet file format and orchestrator poller.
10. Add relay behavior hooks for main-session and Telegram delivery.

Validation:
- packet file created for each dispatch
- question packet emitted by adapter helper
- orchestrator detects unanswered questions and reports them cleanly

### Phase D — cockpit integration
11. Add shared cockpit session naming convention.
12. Keep popen as default launcher.
13. Add tmux launcher behind flag/runtime field.
14. Reuse `R monitor` and/or `codex_panes.py` in a shared session wrapper.

Validation:
- popen path unchanged in simple cases
- tmux path creates deterministic shared session per pipeline
- attach command predictable

### Phase E — migration and docs
15. Document old vs new template format.
16. Migrate one template first (`builder-first-pipeline.md`) as proving ground.
17. Then migrate `research-pipeline.md` and autogate template.
18. Update orchestration skill/docs to reflect adapter-based dispatch instead of OpenClaw-only dispatch.

---

## Risks / Tradeoffs

### Risk 1: too much schema churn at once
Mitigation:
- parser accepts old and new template formats during migration
- only one template migrated first

### Risk 2: question relay becomes coupled to one CLI
Mitigation:
- use packet-based question contract, not CLI-specific parsing alone

### Risk 3: tmux complicates first delivery
Mitigation:
- popen-first implementation
- tmux backend behind runtime switch

### Risk 4: old OpenClaw assumptions still leak through
Examples:
- `WORKSPACE` defaults
- session reset logic
- `openclaw agent` fallback path
Mitigation:
- isolate legacy backend as one adapter
- stop calling it directly from orchestration engine core

### Risk 5: task frontmatter becomes too heavy
Mitigation:
- keep task overrides nested under `pipeline_runtime`
- use symbolic aliases rather than full launch commands where possible

---

## Open Questions Resolved by User in This Session

Resolved:
- CLI-agnostic registry approach: yes
- templates hold phase/stage maps: yes
- overrides live in task frontmatter: yes
- Codex default `--yolo`: yes
- Claude default dangerous skip permissions: yes
- initial implementation may use popen first: yes
- shared cockpit preferred for tmux phase: yes
- design doc + handoff plan needed before code: yes

Still to pin during implementation:
- exact Claude flag string to standardize in registry on this machine
- precise relay path from worker question packet -> Hermes main session vs Telegram direct delivery
- whether pipeline frontmatter should store full resolved runtime snapshot or just pointer to state JSON snapshot

---

## Verification Plan

Read-only planning pass complete. When implementing later, verify with:
- `python3 -m pytest scripts/tests/test_template_parser.py -q`
- `python3 -m pytest scripts/tests/test_cli_registry.py -q`
- `python3 -m pytest scripts/tests/test_runtime_resolution.py -q`
- `python3 -m pytest scripts/tests/test_dispatch_adapters.py -q`
- targeted `orchestration_engine.py dispatch-payload <ref> <agent> --json`
- targeted dry-run launch for one migrated template-backed task

---

## Recommended First Slice

Smallest high-value slice:
1. add CLI registry file
2. add runtime resolution from task frontmatter
3. write dispatch packet files
4. replace direct `openclaw` launch with adapter-based popen launch for Codex/Claude/OpenClaw
5. leave tmux for follow-up

This gets true CLI-agnostic orchestration without overcomplicating first implementation.
