---
primitive: lesson
date: 2026-03-25
source: session:6b7bd235
confidence: high
importance: 4
upstream: [builder-first-pipeline-template-pattern]
downstream: []
tags: [instance:main, pipelines, orchestration, builder-first, gotcha]
---

# pipeline-orchestrate-ignores-template-type-field

## Context

Shael requested launch of the render-engine-simplification pipeline using the builder-first template. Pipeline had `type: builder-first` in frontmatter and a full YAML transitions block in the template file.

## What Happened

`pipeline_orchestrate.py` imported `STAGE_TRANSITIONS` directly from `pipeline_update.py` as a hardcoded global dict. Even though the pipeline had `type: builder-first` set, the orchestrator always used the research-pipeline transition map, which sent the first dispatch to **architect** instead of **builder**. The pipeline was archived and the task was reset to open after the mis-dispatch was caught.

## Lesson

`pipeline_orchestrate.py` must read dynamic transitions via `get_transitions_for_pipeline(version)` — importing hardcoded `STAGE_TRANSITIONS` directly bypasses any per-pipeline template routing.

## Application

Whenever adding a new pipeline type or template, verify that `pipeline_orchestrate.py` (not just `pipeline_update.py`) uses the dynamic resolver. The fix: replace `from pipeline_update import STAGE_TRANSITIONS` with `get_transitions_for_pipeline(version)` calls. Implemented via `scripts/template_parser.py` after this incident.
