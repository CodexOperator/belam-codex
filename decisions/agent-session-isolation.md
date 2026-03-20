---
primitive: decision
status: accepted
date: 2026-03-18
context: "Agent pipelines were stalling because architect/critic/builder shared accumulated session context across multiple pipelines, causing confusion and timeouts"
alternatives:
  - "Subagents (stateless, no memory persistence)"
  - "Separate agent instances with shared sessions (old approach)"
  - "Separate agent instances with fresh sessions per handoff (chosen)"
rationale: "Fresh sessions ensure each pipeline gets undivided agent attention. Memory files provide continuity across sessions without context pollution. One-pipeline-at-a-time prevents overload."
consequences:
  - "Each handoff resets agent main + group sessions via gateway API"
  - "Agents must read memory files at session start for continuity"
  - "Orchestrator auto-writes memory via --learnings flag before handoff"
  - "Checkpoint-and-resume handles timeouts gracefully (up to 5 cycles)"
  - "Stale lock detection (5min) catches hung processes that block dispatch"
  - "One pipeline active at a time — autorun enforces this"
project: snn-applied-finance
tags: [infrastructure, agents, orchestration]
skill: launch-pipeline
upstream: [memory/2026-03-17_134119_major-session-built-three-infrastructure]
downstream: [decision/orchestration-architecture, lesson/checkpoint-and-resume-pattern, memory/2026-03-18_001630_updated-pipeline-orchestratepy-session-r, lesson/session-reset-targets-main-not-group]
---

# Decision: Agent Session Isolation

## Summary
Each agent (architect, critic, builder) gets a completely fresh session for every pipeline handoff. Memory files are the only continuity mechanism.

## Key Components
1. **`reset_agent_session()`** resets both `agent:{name}:main` and `agent:{name}:telegram:group:{id}`
2. **UUID4 session IDs** per handoff — no deterministic reuse
3. **`--learnings` flag** on orchestrator calls auto-writes to agent memory
4. **Checkpoint-and-resume** on timeout: checkpoint → fresh session → resume from memory
5. **Stale lock detection** in `pipeline_autorun.py` — 5min threshold, kills hung PIDs and clears lock files
6. **One-pipeline-at-a-time** enforced by `pipeline_autorun.py`

## Three-Tier Recovery Timeline
| Tier | Threshold | Mechanism | What it catches |
|------|-----------|-----------|-----------------|
| Lock staleness | 5 min | Kill hung PID, clear lock, reset session | Dead/zombied agent processes blocking dispatch |
| Agent timeout | 10 min | Checkpoint partial work, fresh session, resume | Agent taking too long on a stage |
| Pipeline stall | 120 min | Full re-kick with recovery context | Agent completed but handoff failed silently |

## Critical Bug Found
`reset_agent_session()` initially only reset the group session (`telegram:group:...`), but `openclaw agent` CLI uses the `main` session. Old handoff messages accumulated, causing agents to process multiple pipelines simultaneously. Fixed 2026-03-18.
