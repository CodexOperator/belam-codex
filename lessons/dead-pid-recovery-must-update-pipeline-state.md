---
primitive: lesson
date: 2026-03-23
source: pipeline debugging session
confidence: confirmed
importance: 3
upstream: []
downstream: []
tags: [instance:main, pipeline, experiment, recovery, pid]
---

# dead-pid-recovery-must-update-pipeline-state

## Context

`check_running_experiments()` in `pipeline_autorun.py` monitors PID files for running experiments. When it detects a dead process, it checks whether results exist.

## What Happened

The function correctly identified that a dead process had produced complete results (all PKLs present, results_summary.json exists), appended the version to a `completed` list, and returned. But it never called `pipeline_update.py` to transition the status to `experiment_complete`. The analysis gate never opened automatically because the pipeline was stuck at `experiment_running` with a dead PID.

## Lesson

Detecting completion is not the same as recording completion. Any recovery path that confirms a process finished successfully must also update the pipeline state — not just return a flag.

## Application

When writing dead-process recovery logic: always pair the "results exist → success" check with an explicit state transition call. Don't rely on the caller to do it; the recovery function should be self-contained.
