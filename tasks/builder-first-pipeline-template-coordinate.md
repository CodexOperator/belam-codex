---
primitive: task
status: open
priority: high
created: 2026-03-24
owner: belam
depends_on: []
upstream: []
downstream: [render-engine-simplification]
tags: [infrastructure, codex-engine, pipelines, builder-first]
project: codex-engine
---

# Template-Aware Pipeline Orchestration

## Description

Make `pipeline_orchestrate.py` and `pipeline_update.py` template-aware so that pipeline dispatch follows the transition map defined in the template file — not the hardcoded `STAGE_TRANSITIONS` dict.

**Target UX:** `e0 launch t{n} --template builder-first` (or `research`)

## Problem

Today, `STAGE_TRANSITIONS` in `pipeline_update.py` is a single hardcoded dict. Every pipeline follows the same `architect → critic → builder` flow. The builder-first template (`templates/builder-first-pipeline.md`) defines a different flow (`builder → builder → critic → architect`) but the orchestrator ignores it.

## Architecture

### 1. Template Parser (`scripts/template_parser.py` — NEW)

Parse the YAML `transitions:` block from template markdown files. Each template already has machine-readable YAML in a fenced code block:

```python
def parse_template(template_name: str) -> dict:
    """
    Read templates/{template_name}-pipeline.md, extract the YAML code block,
    return a dict with keys:
      - first_agent: str
      - transitions: dict  (same shape as STAGE_TRANSITIONS)
      - status_bumps: dict (same shape as STATUS_BUMPS)
      - start_status_bumps: dict (same shape as START_STATUS_BUMPS)
      - human_gates: list[str]
      - pipeline_fields: dict (type, stages)
    """
```

Parsing rules:
- Find the fenced YAML block between ` ```yaml ` and ` ``` ` under `## Stage Transitions`
- Parse `transitions:` entries — each line is: `stage: [next_stage, agent, message, session: mode]`
- Parse `status_bumps:`, `start_status_bumps:`, `human_gates:` similarly
- Return structured dict matching the shape of existing constants in `pipeline_update.py`

### 2. Pipeline Update Changes (`scripts/pipeline_update.py`)

Add a function to resolve transitions dynamically:

```python
def get_transitions_for_pipeline(version: str) -> tuple[dict, dict, dict, dict]:
    """
    Returns (stage_transitions, block_transitions, status_bumps, start_status_bumps)
    for a given pipeline version.
    
    1. Read pipelines/{version}.md frontmatter → get `type:` field
    2. If type matches a template (e.g. 'builder-first' → templates/builder-first-pipeline.md):
       - Parse template, return its transitions
    3. Else: return the hardcoded STAGE_TRANSITIONS (backward compatible)
    """
```

**Modify existing callers** that reference `STAGE_TRANSITIONS` directly:
- `orchestrate_complete()` in `pipeline_orchestrate.py` — call `get_transitions_for_pipeline(version)` instead of using the global
- Same for `BLOCK_TRANSITIONS`, `STATUS_BUMPS`, `START_STATUS_BUMPS`

### 3. Pipeline Creation Changes (`scripts/launch_pipeline.py`)

Add `--template` flag to `create_pipeline()`:

```python
def create_pipeline(version, description, priority='high', tags=None, project=None,
                    template='research', kickoff=False):
```

When template is specified:
- Parse the template to get `pipeline_fields`
- Set `type:` in frontmatter to template's `pipeline_fields.type` (e.g. `builder-first`)
- Set `first_agent` from template (determines who gets dispatched on kickoff)

### 4. Kickoff Changes (`scripts/pipeline_orchestrate.py`)

The `kickoff` action currently hardcodes completing `pipeline_created` → architect. Change to:
- Read pipeline's `type:` from frontmatter
- Resolve template → get `first_agent`
- Complete `pipeline_created` with transition to `{first_agent}_implement` (or whatever the template says)

## Files to Modify

| File | Change |
|------|--------|
| `scripts/template_parser.py` | **NEW** — template YAML parser |
| `scripts/pipeline_update.py` | Add `get_transitions_for_pipeline()`, keep hardcoded dict as fallback |
| `scripts/pipeline_orchestrate.py` | Use dynamic transitions in `orchestrate_complete()` and `kickoff` |
| `scripts/launch_pipeline.py` | Accept `--template` flag, set pipeline `type:` from template |

## Reference Files
- `templates/builder-first-pipeline.md` — builder-first template with YAML transitions block
- `templates/research-pipeline.md` — research template with YAML transitions block
- `scripts/pipeline_update.py` — current hardcoded `STAGE_TRANSITIONS`, `STATUS_BUMPS`, etc.
- `scripts/pipeline_orchestrate.py` — `orchestrate_complete()`, kickoff logic
- `scripts/launch_pipeline.py` — `create_pipeline()` function

## Phase 2: Coordinate Grammar (pending)

**Target UX:** `e0 launch t{n}.pt{n}`

Example: `e0 launch t4.pt1` = launch task 4 with pipeline template 1

### New namespace: `pt` (pipeline templates)
Register in CODEX.codex so supermap renders:
```
╶─ pt  pipeline-templates (2)
│  ╶─ pt1  builder-first
│  ╶─ pt2  research
```

### `e0 launch` subcommand in `codex_engine.py`
- Parse `t{n}.pt{n}` — resolve task coordinate + template coordinate
- Read task file → extract slug, description, priority, project, tags
- Call `launch_pipeline.py` with `--template {resolved_template_name}` and task fields
- Update task status to `in_pipeline`

### Alternative syntax options (Shael to decide)
- `e0 launch t4.pt1` — dot notation
- `e0 launch t4pt1` — no separator

## Success Criteria
- [ ] `template_parser.py` correctly parses both `builder-first-pipeline.md` and `research-pipeline.md` ✅
- [ ] Existing research pipelines continue to work (backward compatible — no template → use hardcoded) ✅
- [ ] New pipeline with `type: builder-first` dispatches to builder on kickoff (not architect) ✅
- [ ] Builder-first transitions follow: `pipeline_created → builder_implement → builder_bugfix → critic_review → phase1_complete` ✅
- [ ] Human gates from template are respected (no auto-dispatch past them) ✅
- [ ] `launch_pipeline.py --template builder-first` creates pipeline with correct `type:` frontmatter ✅
- [ ] All existing tests/scripts that import `STAGE_TRANSITIONS` still work ✅
- [ ] `pt` namespace in supermap with template coordinates
- [ ] `e0 launch t{n}.pt{n}` wired in `codex_engine.py`
- [ ] End-to-end: `e0 launch t4.pt1` creates pipeline + dispatches correct first agent
