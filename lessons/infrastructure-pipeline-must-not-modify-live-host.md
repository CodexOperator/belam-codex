---
primitive: lesson
importance: 5
tags: [instance:main, containerization, infrastructure, pipeline, safety]
related: [containerization-must-use-isolated-build-directory]
created: 2026-03-24
---

# Infrastructure Pipelines Must Not Modify the Live Host

## What Happened

The `container-build-and-test` pipeline launched with an architect design that called for `sudo` Docker install on the live host. This caused the gateway to shut down and the `openclaw` binary to disappear from PATH. Shael had to restart the gateway manually using a script reference.

## The Lesson

Infrastructure pipelines that install system packages, modify PATH, or touch system-level config **must never run on the live host**. The pipeline was sitting inside the same runtime it was trying to containerize — a clear conflict.

**Isolation rules:**
1. Containerization work → isolated build directory (e.g. `/tmp/container-build/`) that gets deleted after image is confirmed
2. Package installs (apt, brew, pip system-wide) → require explicit human approval or run in sandbox
3. PATH modifications → never from a pipeline; only from a human-approved shell session
4. Any pipeline that could terminate the gateway process must be pre-reviewed before builder stage

## Pattern

Before launching any infrastructure pipeline: check if its deliverables could affect the runtime the pipeline runs on. If yes, require isolation or human gate before builder fires.
