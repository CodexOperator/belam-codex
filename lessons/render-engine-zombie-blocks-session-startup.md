---
primitive: lesson
date: 2026-03-23
source: (add source)
confidence: high
upstream: [decision/codex-cockpit-before-prompt-build-per-turn-injection]
downstream: []
tags: [instance:main, render-engine, session-startup, robustness]
promotion_status: promoted
doctrine_richness: 10
contradicts: []
---

# render-engine-zombie-blocks-session-startup

## Context

Shael asked whether the agent properly spawns into the render engine context on new sessions. Investigation found the render engine process was running but the cockpit plugin was not getting a live UDS socket — zombie processes from prior sessions held the socket file, blocking fresh engine starts.

## What Happened

`codex_render.py` checked socket existence and tried a test connection; if the socket existed but the process was unresponsive (crash/zombie), it raised `RuntimeError("Another render engine is already running")` and aborted. No PID file existed, so there was no way to identify or kill the stale owner. The cockpit plugin's `ensureRenderEngine()` also only waited 500ms for the socket to appear after starting the engine — too short for warm starts.

## Lesson

Socket existence alone is insufficient for render engine startup guard — you need a PID file and a `--force` takeover mode that can kill a stale owner, otherwise any crash leaves new sessions without supermap context injection.

## Application

- Always pair a UDS socket with a PID file for long-running background engines.
- On `--force`: send stop via UDS → wait → read PID file → kill if process is confirmed (check `/proc/{pid}/cmdline`) → unlink socket → start fresh.
- Cockpit plugin must use `--force` on `ensureRenderEngine()` and poll with sufficient timeout (≥3s).
- Applies to any agent-facing background service gated by a socket file.
