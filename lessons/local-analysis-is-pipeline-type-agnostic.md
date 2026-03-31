---
primitive: lesson
date: 2026-03-23
importance: 3
tags: [instance:main, pipeline, infrastructure, local-analysis, autorun]
upstream: [infra-pipelines-use-local-analysis]
downstream: []
promotion_status: exploratory
doctrine_richness: 7
contradicts: []
---

# local-analysis-is-pipeline-type-agnostic

## Lesson

`local_analysis` stages in the pipeline framework are **not** exclusive to SNN research pipelines. Infrastructure pipelines can and should run through them when their experiments complete.

## Context

`research-openclaw-internals` (an infrastructure pipeline — no SNN model, no financial data) reached `local_analysis_complete` after its 7 verification experiments passed. This was correct behavior, not a bug.

Shael confirmed: don't add a type gate. Additional analysis passes are sometimes valuable for infrastructure work too.

## Pattern

- Don't assume `local_analysis` == research pipeline
- `experiment_complete` → `local_analysis` is a general stage transition
- `pipeline_autorun.py` `check_analysis_eligible` should remain type-agnostic
- If a future pipeline genuinely wants to skip analysis, add an explicit `skip_analysis: true` frontmatter flag rather than inferring from type

## Anti-Pattern

```python
# Don't do this:
if fm.get('type') == 'infrastructure':
    continue  # skip analysis
```
