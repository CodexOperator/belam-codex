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
  - "One pipeline active at a time — autorun enforces this"
project: snn-applied-finance
tags: [infrastructure, agents, orchestration]
---

# Decision: Agent Session Isolation

## Summary
Each agent (architect, critic, builder) gets a completely fresh session for every pipeline handoff. Memory files are the only continuity mechanism.

## Key Components
1. **`reset_agent_session()`** resets both `agent:{name}:main` and `agent:{name}:telegram:group:{id}`
2. **UUID4 session IDs** per handoff — no deterministic reuse
3. **`--learnings` flag** on orchestrator calls auto-writes to agent memory
4. **Checkpoint-and-resume** on timeout: checkpoint → fresh session → resume from memory
5. **One-pipeline-at-a-time** enforced by `pipeline_autorun.py`

## Critical Bug Found
`reset_agent_session()` initially only reset the group session (`telegram:group:...`), but `openclaw agent` CLI uses the `main` session. Old handoff messages accumulated, causing agents to process multiple pipelines simultaneously. Fixed 2026-03-18.
