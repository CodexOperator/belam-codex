---
primitive: decision
status: accepted
date: 2026-03-25
context: Pipeline templates existed as markdown files in templates/ but were not addressable as first-class engine coordinates
alternatives: [keep-as-directory-only, use-e3-session-scoped-registration]
rationale: Templates should be navigable and creatable via the same coordinate grammar as other primitives
consequences: [pt-prefix-registered-in-namespace, dynamic-pipeline-templates-resolution, e2-create-supports-pt-prefix]
upstream: [template-aware-pipeline-orchestration, codex-engine-v2-dense-alphanumeric-grammar]
downstream: []
tags: [instance:main, codex-engine, templates, pipelines, namespace]
importance: 4
promotion_status: promoted
doctrine_richness: 10
contradicts: []
---

# templates-directory-as-pt-namespace

## Context

The `templates/` directory held pipeline template markdown files that orchestration scripts read directly by path. They had no coordinate addresses — you couldn't do `pt1` to view a template or `e2 pt "new template"` to create one. The `e0 t1.pt1` syntax existed in the parser but `PIPELINE_TEMPLATES` was a hardcoded dict mapping `{1: 'builder-first', 2: 'research'}`.

## Options Considered

- **Option A:** Keep templates as a plain directory; reference by filename in scripts only
- **Option B:** Register via `e3 category templates` (session-scoped only, not persistent)
- **Option C (chosen):** Add `.namespace` marker with `prefix: pt`, register `pt` in `is_coordinate()`, `PREFIX_TO_CREATE_TYPE`, and resolve `PIPELINE_TEMPLATES` dynamically from the namespace

## Decision

The `templates/` directory is now a first-class namespace with prefix `pt`. Pipeline templates are addressable as `pt1`, `pt2`, etc. The `e0 t1.pt1` coordinate syntax dynamically resolves template indices from the namespace rather than a hardcoded dict. `e2 pt "title"` creates new pipeline templates.

## Consequences

- Any new template file dropped in `templates/` is automatically addressable by index
- Adding new pipeline types doesn't require editing `PIPELINE_TEMPLATES` in the engine
- Multi-char prefix `pt` required explicit addition to `is_coordinate()` regex (same gotcha as `lm`)
- `create_primitive.py` gained a `pipeline-template` type for scaffolding new templates
