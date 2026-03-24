---
primitive: lesson
date: 2026-03-24
source: session-a894056e
confidence: high
importance: 3
upstream: [decision/heartbeat-md-e0-primary-path, decision/remove-e0-sweep-from-heartbeat]
downstream: []
tags: [instance:main, heartbeat, pipeline, rate-limiting, infrastructure]
---

# heartbeat-pipeline-throttle-via-timestamp-gate

## Context

Heartbeat fires every 30 minutes. Task 5 in HEARTBEAT.md launches infra pipelines. Shael wanted to reduce pipeline spawner frequency to every 12 hours without slowing down other heartbeat tasks (git commits, memory consolidation, render health checks).

## What Happened

Instead of changing the global `agents.defaults.heartbeat.every` (which would affect all heartbeat tasks), a timestamp gate was added directly inside Task 5: check `/tmp/openclaw_last_pipeline_check.ts`, skip evaluation if less than 12h has elapsed, update the timestamp after each evaluation. Initial seed timestamp was written immediately to start the 12h window.

## Lesson

When only one task within a shared heartbeat needs rate-limiting, a per-task timestamp gate is better than slowing the global heartbeat interval. Each task can have its own independent cadence without affecting others.

## Application

Use this pattern whenever a heartbeat contains tasks with different desired frequencies. Put the timestamp check at the top of the task block with a clear skip/continue condition. Always update the timestamp at the end of a successful evaluation, not just on action taken.
