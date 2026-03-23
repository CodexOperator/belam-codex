---
primitive: lesson
date: 2026-03-23
source: session a1318751
confidence: high
upstream: [fire-and-forget-dispatch-timeout-1-killed-all-agents]
downstream: []
tags: [instance:main, pipeline, launch, imports, scripting]
---

# launch-pipeline-kickoff-path-had-stale-imports

## Context

Launching t1 (build-codex-layer-v1) via `launch_pipeline.py --kickoff`. Pipeline created successfully but kickoff threw an ImportError immediately.

## What Happened

The `--kickoff` path in `launch_pipeline.py` imported `update_pipeline_status` and `notify_group` from `pipeline_orchestrate`. The function had been renamed to `orchestrate_status` and `notify_group` was removed. The fix was a two-line edit: alias `orchestrate_status as update_pipeline_status` and drop the `notify_group` import (replaced with a bare try/except).

## Lesson

When scripts import from sibling modules with evolving APIs, the callers silently go stale. The kickoff path is rarely exercised, so the breakage went unnoticed until actually launching a pipeline.

## Application

After any rename/removal in `pipeline_orchestrate.py` or `orchestration_engine.py`, grep for callers in `launch_pipeline.py` and `pipeline_autorun.py`. Consider adding a smoke-test for the kickoff path to CI.
