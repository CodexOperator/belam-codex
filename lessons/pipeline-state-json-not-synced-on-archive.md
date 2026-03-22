---
primitive: lesson
date: 2026-03-22
source: main session 2026-03-22
confidence: confirmed
importance: 3
upstream: []
downstream: []
tags: [instance:main, pipeline, bug, infrastructure]
---

# pipeline-state-json-not-synced-on-archive

## Context

The pipeline system stores state in two places: pipeline `.md` files (in `pipelines/`) and `_state.json` files (in `pipeline_builds/`). The `pipeline-context` plugin reads `_state.json` files for boot injection, not the `.md` files.

## What Happened

The `archive_pipeline()` function in `launch_pipeline.py` was correctly updating the pipeline `.md` file to `status: archived`, but never updating the corresponding `_state.json`. As a result, archived pipelines (orch-v1, orch-v2, build-equilibrium-snn, stack-specialists, v4, v4-deep-analysis) continued to show as active at session boot. Fixed by patching the archive function to also write `status: archived` to the state JSON.

## Lesson

Any pipeline state mutation must update **both** the pipeline `.md` AND the `_state.json` file — they are separate stores and both must stay in sync.

## Application

When adding new pipeline state transitions (archive, pause, reset), always update `_state.json` alongside the `.md` file. The `launch_pipeline.py` archive function now does this, but new mutation functions must follow the same pattern.
