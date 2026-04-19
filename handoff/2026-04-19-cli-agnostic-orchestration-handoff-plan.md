# Handoff Plan — CLI-Agnostic Orchestration + Shared Cockpit

Date: 2026-04-19
Workspace: `/home/ubuntu/.hermes/belam-codex`
Status: planning only; no code implementation performed in this pass

## Why this handoff exists

User wants orchestration to stop assuming one agent CLI backend. New target:
- registry/database of CLIs and launch recipes
- templates define only phase/stage topology
- task frontmatter carries runtime overrides
- Codex default launch should use `--yolo`
- Claude default launch should use dangerous skip-permissions mode
- workers must be able to ask questions that relay back through main session and/or Telegram
- initial implementation may use popen first
- later shared tmux cockpit should be supported

## Latest related handoff already on disk

Relevant prior file:
- `handoff/2026-04-19-hermes-cockpit-v1-handoff.md`

That file covers cockpit plugin injection behavior in Hermes.
This new handoff covers orchestration/runtime redesign, not cockpit prompt injection.

## Key repo findings

### Existing strengths
- `scripts/orchestration_engine.py` already has a structured dispatch payload builder.
- `scripts/template_parser.py` already parses stage topology and some runtime metadata.
- `bin/R monitor` already proves a shared tmux monitor pattern.
- `scripts/codex_panes.py` already manages tmux panes.
- `scripts/pipeline_dashboard.py` and `scripts/codex_stream.py` already provide watchable CLI surfaces.

### Main architectural mismatch
- Templates already mention Hermes-style runtime metadata.
- Actual dispatch still launches `openclaw agent` directly via `subprocess.Popen`.
- Therefore topology is becoming generic, but executor is still hardwired.

## Desired architecture

### 1. Separate topology from execution
Templates should answer:
- what phases exist
- which stages are in each phase
- which symbolic CLI ref each stage prefers
- whether the phase has a human gate
- whether the phase repeats once / several / indefinite

Runtime executor should answer:
- what concrete program to launch
- with what args
- with popen or tmux
- how to resume / attach / relay questions

### 2. Introduce CLI registry
Planned new file:
- `state/cli_registry.json`

Registry stores:
- program name
- default args
- launcher preference
- supports_tmux
- supports_resume
- question relay strategy
- packet entry mode

### 3. Move overrides into task frontmatter
Tasks should become the authoritative place for:
- template path
- symbolic cli alias mapping
- phase-level overrides
- stage-level overrides
- launcher mode override
- ask/relay behavior override

### 4. Use packetized dispatch
Each stage dispatch should materialize a packet file under pipeline build state.
Then adapters launch a CLI against that file rather than stuffing giant prompts into shell args.

### 5. Deliver in two runtime steps
Step 1:
- popen-first backend
- adapter-driven Codex / Claude / OpenClaw execution

Step 2:
- shared tmux cockpit session per pipeline
- deterministic attach/restart/log flow

## Files likely to change in implementation pass

New files expected:
- `scripts/cli_registry.py`
- `scripts/dispatch_adapters.py`
- `scripts/runtime_resolution.py`
- `scripts/agent_questions.py`
- `state/cli_registry.json`

Existing files likely to change:
- `scripts/orchestration_engine.py`
- `scripts/template_parser.py`
- `scripts/launch_pipeline.py`
- `scripts/pipeline_orchestrate.py`
- `schemas/task.md`
- `templates/builder-first-pipeline.md`
- `templates/builder-first-autogate-pipeline.md`
- `templates/research-pipeline.md`
- `bin/R` (later tmux attach/status helpers)

## Recommended implementation order

### Slice 1 — minimal useful backend abstraction
1. Add `state/cli_registry.json`
2. Add loader/helper in `scripts/cli_registry.py`
3. Extend task schema for runtime override block
4. Add runtime resolution helper
5. Refactor `orchestration_engine.py` to dispatch via adapter instead of direct `openclaw` call
6. Keep launch mode = popen only

Goal:
- same orchestration flow
- new CLI-agnostic backend
- Codex and Claude selectable by task/stage

### Slice 2 — dispatch packets + question relay
7. Write per-stage packet files
8. Add worker question packet format
9. Add relay polling/reporting path to main session / Telegram

Goal:
- human clarification loop works cleanly
- worker CLIs can pause for answers without hidden state

### Slice 3 — template format migration
10. Extend parser to support `path:` topology format
11. Preserve compatibility with current templates
12. Migrate one template first, preferably `builder-first-pipeline.md`
13. Then migrate `research-pipeline.md`

Goal:
- templates become topology-only
- runtime overrides live in tasks as requested

### Slice 4 — shared tmux cockpit
14. Add tmux launcher backend
15. Use one shared session per pipeline
16. Reuse `R monitor` / `codex_panes.py` pieces
17. Add attach/status commands

Goal:
- human-visible shared cockpit without disturbing popen-first path

## Risks to watch
- Template migration too early can break stage parsing.
- OpenClaw assumptions still embedded in fallback code and session reset paths.
- Claude launch flags must be verified on this machine before hardcoding exact default arg string.
- Question relay can sprawl if done before packet contract is stabilized.

## Explicit user decisions from this session
- CLI-agnostic registry/database: yes
- Templates should define topology only: yes
- Task frontmatter should carry runtime overrides: yes
- Codex default dangerous mode: `--yolo`
- Claude default dangerous mode: yes, dangerous skip permissions by default
- Popen first acceptable if tmux complicates flow: yes
- Shared cockpit preferred: yes
- This pass should produce design doc + handoff plan only: yes

## Verification for future implementation
When coding starts, validate with:
- parser tests for old + new template formats
- runtime resolution tests for task override precedence
- adapter command-build tests for Codex/Claude/OpenClaw
- dry-run dispatch for one real pipeline
- later tmux smoke test using shared session naming

## Artifacts created in this planning pass
- `.hermes/plans/2026-04-19_210618-cli-agnostic-orchestration-design.md`
- `handoff/2026-04-19-cli-agnostic-orchestration-handoff-plan.md`

## Suggested next prompt

Use `.hermes/plans/2026-04-19_210618-cli-agnostic-orchestration-design.md` and `handoff/2026-04-19-cli-agnostic-orchestration-handoff-plan.md` as starting context. Implement Slice 1 only: CLI registry, task-frontmatter runtime overrides, adapter-based popen dispatch, no tmux yet.
