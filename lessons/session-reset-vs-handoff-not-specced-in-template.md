---
primitive: lesson
date: 2026-03-24
source: session-4fc7e8af
confidence: medium
upstream: [builder-first-pipeline-template-pattern]
downstream: []
tags: [instance:main, pipeline, orchestration, session-reset, template, spec]
importance: 3
---

# session-reset-vs-handoff-not-specced-in-template

## Context

Builder-first pipeline template was being refined with human gates and the complete-task command. Shael asked whether templates formally specify when a stage transition spawns a fresh agent session vs continues in the same session.

## What Happened

The orchestrator (`pipeline_orchestrate.py`) calls `reset_agent_session()` on most transitions, but this behavior is not formally documented in the pipeline templates (e.g., `builder-first-pipeline.md`). Each stage definition doesn't declare a `session_mode: fresh | continue` field. Shael identified this as a gap worth formalizing.

## Lesson

Pipeline templates currently don't specify `fresh session` vs `same-session handoff` per stage. This is implicit behavior in the orchestrator — not a first-class spec. A formal `session_mode` field per stage transition would make this visible and controllable.

## Application

When formalizing pipeline stage specs, add a `session_mode` field (or similar) to each stage definition. Proposed: `session_mode: fresh` (default — calls `reset_agent_session`) vs `session_mode: continue` (same session handoff, no reset). This is pending implementation.
