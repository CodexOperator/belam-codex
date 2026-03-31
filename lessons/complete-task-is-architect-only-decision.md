---
primitive: lesson
date: 2026-03-24
source: session-4fc7e8af
confidence: high
upstream: [builder-first-pipeline-template-pattern]
downstream: []
tags: [instance:main, pipeline, orchestration, critic, architect, role-separation]
importance: 3
promotion_status: promoted
doctrine_richness: 9
contradicts: []
---

# complete-task-is-architect-only-decision

## Context

Building out the builder-first pipeline template with human gates. The complete-task command was added to allow an agent to archive the pipeline and mark the parent task done in one shot. The generic handoff message was shared by all agents.

## What Happened

Shael noticed that the critic was seeing the `complete-task` option in its handoff message, which could cause the critic to make an "is this task fully done?" judgment that belongs only to the architect. The fix: make the `complete-task` block in `build_handoff_message()` conditional on `next_agent == 'architect'`.

## Lesson

The `complete-task` decision (archive pipeline + mark task done) belongs to the **architect only**. The critic's only choices are block (task not fulfilled) vs complete-stage (pass findings forward). Never show `complete-task` to critic or builder.

## Application

When adding new orchestrator commands that change pipeline/task lifecycle, always scope which agent roles should see them in handoff messages. Role-specific instructions prevent agents from making decisions outside their scope.
