---
primitive: decision
date: 2026-03-23
status: accepted
upstream: [pipeline-state-json-not-synced-on-archive]
downstream: []
tags: [instance:main, orchestration, pipeline, infra]
---

# consolidate-pipeline-state-json-to-workspace-builds-dir

## Context

Pipeline artifacts are split across two `pipeline_builds/` directories:
- **workspace** `pipeline_builds/` — newer pipeline .md files (codex-engine-v3, legendary-map)
- **research repo** `machinelearning/snn_applied_finance/research/pipeline_builds/` — all state JSONs + older .md files

`BUILDS_DIR` in `orchestration_engine.py` and `pipeline_autorun.py` points to the research path. Infra pipelines started living in workspace but their state JSONs stayed in research.

## Decision

Consolidate all pipeline state JSONs into workspace `pipeline_builds/` alongside the pipeline primitive `.md` files. Update `BUILDS_DIR` constant in both `orchestration_engine.py` and `pipeline_autorun.py`, and in the `pipeline-dispatch` hook. Migrate existing state JSONs.

## Rationale

- Pipeline primitives (the source of truth) already live in workspace `pipeline_builds/`
- Having state in a different repo introduces confusion and makes the `_state.json` "missing" from the main workspace view
- Consistency: all pipeline artifacts in one place
- The research repo `pipeline_builds/` can be kept for historical reference but shouldn't be the live write target

## Trade-offs

- Migration step needed for active pipelines
- The pipeline-dispatch hook (TypeScript) also needs updating
- Older SNN research pipelines have state in research — those can stay or be migrated gradually
