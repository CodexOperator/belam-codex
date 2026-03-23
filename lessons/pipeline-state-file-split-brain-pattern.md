---
primitive: lesson
date: 2026-03-23
source: pipeline debugging session
confidence: confirmed
importance: 4
upstream: []
downstream: []
tags: [instance:main, pipeline, state-file, bug]
---

# pipeline-state-file-split-brain-pattern

## Context

Pipeline infrastructure evolved from a flat state file layout (`{version}_state.json`) to a subdirectory layout (`{version}/_state.json`). Not all scripts were updated consistently.

## What Happened

`pipeline_update.py` wrote state to the flat path. `load_state_json()` in the sweep (and autorun) preferred the subdirectory path. When both files existed, the sweep always saw the subdirectory version (stale), even after pipeline_update.py had correctly advanced the state. p2 (limbic-reward-snn) appeared as `phase1_complete` in sweeps despite a fully complete experiment.

## Lesson

When a codebase has two versions of a file layout, every reader and every writer must agree on the priority order — or you get silent split-brain where writers succeed but readers see stale data.

## Application

Whenever a new path convention is introduced, audit all `load_*` and `save_*` functions across all scripts that touch that path. Prefer a single canonical writer function used everywhere. After fixing, verify by running a dry-run sweep and confirming both paths are consistent.
