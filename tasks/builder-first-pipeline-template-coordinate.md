---
primitive: task
status: open
priority: medium
created: 2026-03-24
owner: belam
depends_on: []
upstream: []
downstream: []
tags: [infrastructure, codex-engine, pipelines, builder-first]
project: codex-engine
---

# Builder-First Pipeline Template as Coordinate Action

## Description

Make `templates/builder-first-pipeline.md` usable programmatically through the coordinate system. Target UX:

```
e0 t{n} --template builder-first
```

Auto-creates the subtask sequence (builder_implement → builder_bugfix → critic_review → architect_phase2) and dispatches to builder instead of architect.

## Scope

1. `e0` recognizes `--template` flag
2. Template files in `templates/` define stage sequences and dispatch targets
3. `launch_pipeline.py` accepts template parameter, creates pipeline with correct stage order
4. Pipeline orchestrator follows template stage order for handoffs

## Depends On
- Render engine simplification (for clean codex engine to extend)
- Existing pipeline orchestration infrastructure
