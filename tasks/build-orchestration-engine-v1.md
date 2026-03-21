---
primitive: task
status: open
priority: critical
created: 2026-03-21
owner: belam
project: multi-agent-infrastructure
depends_on: [build-codex-engine]
upstream: [decision/orchestration-architecture, decision/codex-engine-v1-architecture]
downstream: [spiking-transformer-integration-research, codex-engine-v3-temporal-mcp-autoclave]
tags: [orchestration, engine, infrastructure, v1]
---

# Orchestration Engine v1: Codex-Native Pipeline Automation

## Overview

Replace the current script-based orchestration (`pipeline_orchestrate.py`, `pipeline_autorun.py`, `launch_pipeline.py`) with a unified orchestration engine that speaks codex-native coordinates. Addressable via `e0` from the codex engine.

## Context

Current state: 3 separate Python scripts with overlapping concerns, ~2500 lines total. They work but are duct-taped — file-path based, no coordinate awareness, manual gate logic, fragile lock detection. The orchestration engine makes all of this addressable through the codex coordinate system.

## 1. Unified Orchestration Interface

### Via Codex Engine
- `e0` routes to orchestration engine
- `e0p3` — orchestrate pipeline 3 (status, next action, dispatch)
- `e0h` — handoff check (replaces `--check-pending`)
- `e0g` — gate check (replaces `--check-gates`)
- `e0s` — stall detection (replaces threshold scan)
- `e0` bare — full orchestration sweep (replaces `pipeline_autorun.py`)

### Standalone
- `belam orchestrate` — full sweep, same as heartbeat Task 1
- Can run headless (cron, heartbeat) or interactive

## 2. Pipeline Lifecycle (codex-native)

### Pipeline as Primitive
- Pipelines already live in `pipelines/*.md` with frontmatter
- Orchestration engine reads/writes pipeline state via codex coordinates
- Status transitions produce F-label diffs: `F1 Δ p3.stage architect_design → critic_review`

### Gate Logic
- Gates defined as primitive fields (not hardcoded in scripts)
- `e0g p3` checks gates for pipeline 3, returns which are open/blocked
- Gate dependencies expressible as coordinate references: "p3 blocked until p2.stage = phase2_complete"

### Agent Dispatch
- `e0p3 dispatch architect` — spawn architect agent for pipeline 3
- Session isolation maintained (fresh session per handoff)
- Memory injection: agent gets pipeline context + relevant primitives via codex engine
- Replaces manual `sessions_spawn` + prompt assembly

## 3. Handoff Engine

### Current Problem
Handoffs are script-mediated file operations with manual prompt construction.

### Target
- Handoff is a first-class operation: `e0p3 handoff architect→critic`
- Orchestration engine:
  1. Captures architect output
  2. Constructs critic context (pipeline state + design doc + review checklist)
  3. Spawns critic session with codex-native context injection
  4. Records handoff as primitive event
- Checkpoint-and-resume built in: if agent times out, `e0p3 resume` picks up from last checkpoint

## 4. Lock Management

- Session locks tracked as ephemeral state (RAM tree from codex v2, or simple PID files)
- Stale lock detection: process alive check, not just age threshold
- `e0 locks` — show all active locks
- `e0 unlock p3` — force-release a lock

## 5. Consolidate Scripts

### Retire
- `pipeline_autorun.py` → absorbed into `e0` sweep
- `pipeline_orchestrate.py` → absorbed into handoff engine
- `launch_pipeline.py` → absorbed into `e0p3 launch` / `e2p`

### Keep (refactored)
- Core orchestration logic extracted into `scripts/orchestration_engine.py`
- Codex engine calls this module when `e0` is invoked
- Standalone CLI preserved: `belam orchestrate` for headless use

## Acceptance Criteria

- [ ] `e0` sweep replaces `pipeline_autorun.py` functionality
- [ ] `e0p3` shows pipeline status + next action
- [ ] `e0h` replaces `--check-pending` handoff check
- [ ] `e0g` replaces `--check-gates` gate check
- [ ] Agent dispatch via `e0p3 dispatch <role>`
- [ ] Handoff engine: `e0p3 handoff A→B` with context assembly
- [ ] Checkpoint-and-resume: `e0p3 resume`
- [ ] Lock management: `e0 locks`, `e0 unlock`
- [ ] Legacy scripts deprecated with warnings
- [ ] Heartbeat Task 1 updated to use `e0` sweep

## 6. Hook Integration (from research-openclaw-internals)

Research pipeline delivered 3 plugin prototypes and cataloged 27 hooks. Orch V1 should wire these in:

### Available Hooks for Orchestration
- **`before_prompt_build`** — inject active pipeline state into agent context automatically
- **`agent:bootstrap`** — session-start context injection (supermap already uses this)
- **`after_tool_call`** — intercept tool results for structured logging
- **`agent_end`** — capture final messages + metadata for handoff records

### Plugin Prototypes Ready to Deploy
| Plugin | Status | What it does |
|--------|--------|-------------|
| `pipeline-context` | Built, verified | Auto-injects pipeline state via `before_prompt_build` |
| `pipeline-commands` | Built, verified | `/pipelines` and `/pstatus` slash commands |
| `agent-turn-logger` | Built, verified | JSONL logging using both hook layers |

### Pre-work: Hook Verification Scripts
Before wiring e0 to dispatch agents through hooks, build verification scripts that:
- [ ] Test `before_prompt_build` injection end-to-end (agent actually sees pipeline context)
- [ ] Test agent dispatch via `sessions_spawn` with pipeline context pre-loaded
- [ ] Verify hook naming conventions (colons for internal, underscores for plugin)
- [ ] Test `agent_end` hook captures handoff-relevant metadata

Reference: `machinelearning/snn_applied_finance/research/pipeline_builds/research-openclaw-internals_builder_reference.md`

## Dependencies
- Codex Engine v1 (complete) — coordinate system foundation
- Codex Engine v2 (next) — dense grammar, e0 mode routing
- research-openclaw-internals pipeline (complete) — hook architecture findings, 3 plugin prototypes
- `decisions/orchestration-architecture.md` — current architecture decisions
- `lessons/checkpoint-and-resume-pattern.md` — timeout recovery

## Notes
- The orchestration engine is a *consumer* of the codex engine, not part of it
- `e0` is a codex coordinate that routes to orchestration — same way `e1t12` routes to a task edit
- Pipeline state transitions should produce F-label diffs visible in the supermap
- Hook integration prerequisite: build test scripts before wiring production dispatch (folded from research-orchestration-tooling task)

