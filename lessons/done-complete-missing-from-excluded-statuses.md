---
primitive: lesson
date: 2026-03-25
source: main session f51170a6
confidence: high
upstream: []
downstream: []
tags: [instance:main, codex-engine, task-management, filtering]
importance: 3
promotion_status: candidate
doctrine_richness: 8
contradicts: []
---

# done-complete-missing-from-excluded-statuses

## Context

User noticed that tasks marked as done/complete were still appearing in default views (`R t`, `R r0`) even after `mark-completed` had been run on them.

## What Happened

`EXCLUDED_STATUSES` in `codex_engine.py` only contained `{'superseded', 'archived'}`. The terminal statuses `'done'` and `'complete'` were absent, so tasks in those states stayed visible in all default active listings. Adding both to `EXCLUDED_STATUSES` reduced the visible task count from 55 to 25.

## Lesson

`done` and `complete` are terminal statuses that should be excluded from default views just like `archived` and `superseded` — they must be explicitly added to `EXCLUDED_STATUSES` or they will clutter active task listings.

## Application

Whenever new terminal statuses are introduced in the codex engine, immediately verify they appear in `EXCLUDED_STATUSES`. Default views should only show actionable work.
