---
primitive: decision
status: accepted
date: 2026-03-14
context: Multi-agent design for SNN finance research
alternatives: [single agent, pair (proposer+builder), full team (5+ roles)]
rationale: Three specialized roles cover the full research cycle. Architect holds the design space and makes structural decisions. Critic validates statistical rigor, detects hype, and prevents overfitting. Builder implements with production-quality code. The trio generates interference patterns between perspectives that single-agent can't reach.
consequences: [Each agent has dedicated Telegram bot, role-specific knowledge files guide behavior, sessions_send for inter-agent comms, filesystem is shared state]
project: multi-agent-infrastructure
tags: [agents, architecture, decision]
skill: pipelines
upstream: []
---

# Architect / Critic / Builder Agent Trio

## Architect (@BelamArchitectBot)
- System design, architecture selection, meta-patterns
- Reads: ARCHITECT_KNOWLEDGE.md
- Decides WHAT to build and WHY

## Critic (@BelamCriticBot)
- Statistical hygiene, overfitting detection, hype assessment
- Reads: CRITIC_KNOWLEDGE.md
- Validates proposals BEFORE building, reviews results AFTER

## Builder (@BelamBuilderBot)
- Implementation, code patterns, GPU optimization
- Reads: BUILDER_KNOWLEDGE.md
- Turns validated designs into runnable code

## Protocol
Shael kicks off in group → Architect designs → Critic reviews → Builder implements → Critic code-reviews → deliverable posted to group.

All agents inherit from AGENT_SOUL.md — they are Belam, operating as specialized resonance modes.
