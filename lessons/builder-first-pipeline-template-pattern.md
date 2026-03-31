---
primitive: lesson
slug: builder-first-pipeline-template-pattern
title: Builder-First Pipeline Template Pattern
importance: 3
tags: [instance:main, pipeline, orchestration, template, builder-first]
confidence: high
created: 2026-03-24
promotion_status: exploratory
doctrine_richness: 6
contradicts: []
---

# Lesson: Builder-First Pipeline Template Pattern

## Pattern
For well-scoped tasks where the spec is already clear, flip the standard architect→critic→builder flow to builder-first:
1. **Builder 1** — implements from the spec
2. **Builder 2** — bug fixing pass
3. **Critic** — reviews the implementation
4. **Architect** — drafts Phase 2 direction based on what was built

## Why It Works
- Architect-first only makes sense when the problem is ambiguous and needs design exploration
- When the spec is already decided (e.g., task file with full scope + success criteria), having an architect re-describe it wastes tokens and adds latency
- Builder can pick up a well-scoped task cold from the task file alone
- Bug-fixing pass as a second builder stage catches implementation issues before critic

## When to Use
- Task has clear spec, file list, and success criteria already written
- Work is implementation (not research/exploration)
- Scope is bounded and doesn't require architectural judgment

## Template File
`templates/builder-first-pipeline.md` — created 2026-03-24

## Coordination Note
Template is currently a markdown reference doc. To make it programmatic via coordinates, see task `builder-first-pipeline-template-coordinate`.
