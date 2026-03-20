---
primitive: decision
status: accepted
date: 2026-03-18
context: "Pipeline work between agents (architect/critic/builder) needed reliable handoffs, timeout recovery, and hung-process detection — without human intervention"
alternatives:
  - "Direct sessions_send between agents (no central orchestrator) — fragile, no recovery"
  - "Subagent spawning per stage (stateless, no memory persistence) — loses continuity"
  - "Central orchestrator with three-tier recovery (chosen)"
rationale: "A central script (pipeline_orchestrate.py) as the single handoff path ensures every transition gets memory consolidation, session reset, state updates, and notifications. pipeline_autorun.py adds event-driven automation on top. Together they create a self-healing pipeline system."
consequences:
  - "All agent stage transitions MUST go through pipeline_orchestrate.py — no direct sessions_send"
  - "Three-tier recovery: 5min lock staleness, 10min checkpoint-and-resume, 120min stall re-kick"
  - "One pipeline active at a time — prevents agent context overload"
  - "Heartbeat becomes code-driven (pipeline_autorun.py) rather than LLM-decided"
  - "Agent memory files are the only continuity mechanism across sessions"
project: snn-applied-finance
tags: [infrastructure, orchestration, agents, architecture]
skill: orchestration
cli: "belam autorun, belam orchestrate, belam revise, belam handoffs"
upstream: [decision/agent-session-isolation, memory/2026-03-17_134119_major-session-built-three-infrastructure]
downstream: [lesson/checkpoint-and-resume-pattern, memory/2026-03-18_233943_built-phase-1-revision-system-new-stages]
---

# Decision: Centralized Orchestration Architecture

## Summary

Two scripts form the orchestration layer:
- **`pipeline_orchestrate.py`** — the handoff engine (agent-facing). Handles every stage transition: memory consolidation, state updates, session reset, agent wake, checkpoint-and-resume on timeout.
- **`pipeline_autorun.py`** — the automation layer (heartbeat-facing). Runs deterministic checks: stale locks (5min), gate openings, pipeline stalls (120min). No LLM judgment needed.

## Why Centralized

Early attempts had agents calling `sessions_send` directly to each other. Problems:
1. No memory consolidation — agents lost context across sessions
2. No timeout recovery — hung agents blocked the entire pipeline indefinitely
3. No state tracking — pipeline markdown and JSON fell out of sync
4. No notifications — humans couldn't see progress without manually checking

The orchestrator solves all four by being the single path for all transitions.

## Three-Tier Recovery

| Tier | Threshold | Mechanism | Script |
|------|-----------|-----------|--------|
| Lock staleness | 5 min | Kill hung PID, clear lock file, reset session | `pipeline_autorun.py` |
| Agent timeout | 10 min | Checkpoint partial work, fresh session, resume (up to 5×) | `pipeline_orchestrate.py` |
| Pipeline stall | 120 min | Full re-kick with recovery context | `pipeline_autorun.py` |

These tiers are complementary:
- **Tier 1** catches processes that died or zombied (OS-level failure)
- **Tier 2** catches agents that are working but too slowly (task complexity)
- **Tier 3** catches cases where the handoff itself failed silently (network/gateway issues)

## One-Pipeline-at-a-Time

Agents share a single set of instances (one architect, one critic, one builder). Running multiple pipelines simultaneously caused context bleeding — agents confused which pipeline they were working on. The `pipeline_autorun.py` enforces one active pipeline by checking `last_updated` timestamps against the stall threshold window.

## Key Design Choices

1. **Fresh UUID4 sessions, not deterministic** — UUID5 caused session reuse and context pollution
2. **Memory files as continuity, not session history** — survives resets, portable, human-readable
3. **Auto memory via `--learnings` flag** — agents don't need to remember to save; orchestrator guarantees it
4. **Both session keys reset** — `main` (CLI) and `telegram:group:*` (group chat) must both be cleared
5. **Lock files checked before everything else** — a stale lock blocks all other recovery mechanisms

## Evolution

- **v1** (2026-03-17): Direct `sessions_send` between agents, no recovery
- **v2** (2026-03-18 AM): Central orchestrator with session reset + memory consolidation
- **v3** (2026-03-18 PM): Added checkpoint-and-resume (10min timeout), stall detection (120min)
- **v4** (2026-03-18 evening): Added stale lock detection (5min) after discovering hung processes block dispatch indefinitely

## Related

- `decisions/agent-session-isolation.md` — fresh sessions per handoff
- `lessons/checkpoint-and-resume-pattern.md` — tier 2 recovery details
- `lessons/session-reset-targets-main-not-group.md` — must reset both session keys
- `skills/orchestration/SKILL.md` — full usage reference for agents
