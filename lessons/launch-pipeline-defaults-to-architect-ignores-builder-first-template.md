---
primitive: lesson
date: 2026-03-25
source: main session 2026-03-25T03:20
confidence: high
upstream: [decision/template-aware-pipeline-orchestration, lesson/pipeline-orchestrate-ignores-template-type-field]
downstream: []
tags: [instance:main, pipeline, builder-first, orchestration, bug]
promotion_status: promoted
doctrine_richness: 10
contradicts: []
---

# launch-pipeline-defaults-to-architect-ignores-builder-first-template

## Context

Launched `setup-vectorbt-nautilus-pipeline-s1-environment-setup` via `launch_pipeline.py --kickoff`. The task file correctly specifies `type: builder-first`. The template-aware orchestration refactor was supposed to fix this.

## What Happened

The pipeline kicked off as `architect_design` (dispatching the architect agent) despite the pipeline type being `builder-first`. Root cause in `launch_pipeline.py`: when `resolve_transition()` returns no matching transition for `pipeline_created`, the code falls back to `first_stage, first_agent = 'architect_design', 'architect'` hardcoded. This bypass ignores the template type field entirely.

## Lesson

`launch_pipeline.py` has a hardcoded fallback to `architect_design` when `resolve_transition()` returns `None` for the `pipeline_created` event. The template-aware refactor must ensure `resolve_transition()` handles `pipeline_created` for all template types — or the fallback must read the template type before defaulting.

## Application

- After any template-aware orchestration refactor, verify by launching a builder-first pipeline and checking that the first dispatched agent is `builder`, not `architect`.
- Fix: `resolve_transition()` should handle `pipeline_created` → `p1_builder_implement` for builder-first templates. The hardcoded fallback is a regression risk for every new template type added.
