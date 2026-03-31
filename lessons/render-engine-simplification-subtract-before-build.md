---
primitive: lesson
slug: render-engine-simplification-subtract-before-build
title: Subtract First, Then Build — Render Engine Simplification Order
importance: 3
tags: [instance:main, render-engine, simplification, architecture, sequencing]
confidence: high
created: 2026-03-24
promotion_status: exploratory
doctrine_richness: 6
contradicts: []
---

# Lesson: Subtract First, Then Build

## Pattern
When simplifying a system while simultaneously adding new capabilities, **do the removal first** before building the replacement. The simplification step (pure subtraction) should not depend on the new features.

## Applied Context
Render engine simplification (kill R labels, inotify chain, HeartbeatTrigger, DiffEntry) does NOT depend on RAM git worktree existing. So:
1. `render-engine-simplification` — pure subtraction, can run immediately
2. `ram-git-s1` through `ram-git-s4` — builds the new system on the cleaned foundation

Attempting to build RAM git while the old system is still in place creates surface area for conflicts and makes both changes harder to test.

## Why It Matters
- Subtraction tasks are lower risk (removing code that was causing bugs)
- A cleaned codebase is easier to build on top of
- Testing is clearer: verify the old system is gone, then verify the new one works
- Smaller, focused PRs / agent tasks are easier to review
