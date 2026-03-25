---
primitive: decision
date: 2026-03-25
status: implemented
importance: 4
upstream: [builder-first-pipeline-template-pattern, orchestration-architecture]
downstream: []
tags: [instance:main, pipelines, orchestration, builder-first, templates, infrastructure]
---

# template-aware-pipeline-orchestration

## Decision

Pipeline orchestration reads transition maps dynamically from template YAML blocks rather than using hardcoded global dicts. The pipeline's `type:` frontmatter field determines which template file to parse.

## Rationale

- Hardcoded `STAGE_TRANSITIONS` in `pipeline_update.py` forced all pipelines through the research-pipeline flow regardless of their `type:` field
- Builder-first pipelines need to dispatch to `builder` first, not `architect`
- Adding new pipeline types shouldn't require editing core orchestration code
- Template YAML already exists in `templates/*.md` — parsing it is the natural extension point

## Implementation

- **`scripts/template_parser.py`** (new): Parses `## Stage Transitions` YAML block from template markdown. Uses PyYAML with regex fallback. Caches parsed templates. Exports `get_first_agent()`, `get_transitions()`, `get_human_gates()`.
- **`pipeline_update.py`**: `get_transitions_for_pipeline(version)` reads pipeline `type:` frontmatter and calls template_parser. Falls back to hardcoded dicts for `research` type and unknowns (backward compatible).
- **`pipeline_orchestrate.py`**: `orchestrate_complete()` and `orchestrate_block()` call `get_transitions_for_pipeline(version)` instead of importing hardcoded globals.
- **`launch_pipeline.py`**: `--template` flag sets `type:` from template's `pipeline_fields.type`.

## Consequences

- All new pipeline types are defined by their template file — no core code changes needed
- Research pipelines unchanged (type: research → hardcoded fallback)
- 11/11 tests passing post-implementation
- Triggered by: architect mis-dispatch on render-engine-simplification pipeline (first launch attempt)
