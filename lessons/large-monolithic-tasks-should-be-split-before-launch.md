---
primitive: lesson
importance: 4
tags: [instance:main, task-management, codex-engine, architecture]
related: [codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing]
created: 2026-03-24
promotion_status: exploratory
doctrine_richness: 6
contradicts: []
---

# Large Monolithic Tasks Should Be Split Before Launch

## What Happened

The V4 task (`codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing`) had D1-D6 (RAM-first render runtime) AND D7.1-D7.8 (symlink + RAM git worktree) all crammed together. Similarly, `limit-soul-read-write` bundled 4-5 distinct features into one task. Both needed splitting before any launch could happen productively.

## The Lesson

A task with 3+ independent deliverables that could each be their own pipeline should be split *before* it enters a pipeline. Signs it's too big:

- "D7 has 8 sub-items that are each independent systems"
- "This task bundles A + B + C and they have different owners/timelines"
- Depends-on chains longer than 2 hops suggest the task is actually a project

**Split heuristic:** If any two deliverables could be done in parallel by different agents without conflict, they belong in separate tasks.

## Pattern

When reviewing the task queue for launch candidates, do a quick "is this splittable?" check. If yes, split first, then launch the most foundational piece. Supersede the parent task, don't delete it — the overview context is valuable.
