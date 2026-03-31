---
primitive: lesson
date: 2026-03-23
source: render-engine debugging session
confidence: high
importance: 4
upstream: [render-engine-pid-file-and-force-flag]
downstream: []
tags: [instance:main, render-engine, inotify, debugging, codex-engine-v4]
promotion_status: promoted
doctrine_richness: 7
contradicts: []
---

# inotify-batch-creates-coalesce-to-single-reindex

## Context

Testing diff-triggered heartbeat by burst-creating 12 files. Expected 12 DiffEntry creates; got 1.

## What Happened

Rapid file creation triggers `_on_file_change('created')` 12 times in quick succession. Each call
invokes `_reindex_single_new`, which calls `reindex_namespace` — a full namespace reload. The first
reindex loads all 12 files at once. The remaining 11 callbacks also trigger full reindexes but find
"nothing new" (files already indexed) and return only 1 DiffEntry total. Additionally,
`_filepath_to_coord` lookup failed in test runs due to relative vs. absolute path mismatch.

## Lesson

When inotify events fire for batch file operations, each callback triggers a full namespace
reindex — only the first reindex produces diffs; subsequent ones are redundant no-ops returning
nothing new.

## Application

- `_reindex_single_new` must return **all** new files found during a reindex (not just the
  triggering file), so all 12 get DiffEntries from the first callback.
- Subsequent callbacks must check if file is already diffed and skip redundant reindexes.
- `apply_disk_change` return type must be updated from `DiffEntry | None` to `list[DiffEntry]`
  and all callers updated accordingly.
- Always use absolute paths (`.resolve()`) when comparing workspace paths against inotify events.
