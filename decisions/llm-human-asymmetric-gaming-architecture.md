---
primitive: decision
status: accepted
date: 2026-03-26
context: LLM gaming research task creation
alternatives:
  - symmetric multiplayer (LLM plays same role as humans)
  - fully cooperative (no adversarial element)
rationale: Asymmetric roles leverage LLM strengths — world simulation, NPC control, resource management — while keeping human gameplay tactile and direct
consequences:
  - Resource tracking required on both sides (mana/minions vs hero HP/gold)
  - LLM must be constrained to prevent degenerate domination strategies
  - Fog of war natural fit for the asymmetry
upstream: []
downstream: []
tags: [instance:main, gaming, research, design, llm]
---

# llm-human-asymmetric-gaming-architecture

## Context

Designing LLM-human interactive game formats where both sides are genuinely engaged. The question was whether to make LLM and humans play symmetric roles or leverage the different strengths of each.

## Options Considered

- **Symmetric:** LLM and human play the same role (e.g., both as nations in Civ-lite). Interesting but doesn't exploit LLM unique capabilities.
- **Asymmetric — LLM as environment/dungeon master:** LLM manages world state, spawns obstacles, controls NPCs; human navigates as hero or party. Natural division of labor.
- **Cooperative only:** Both sides work together. Simpler but lacks tension.

## Decision

Asymmetric game design where LLM controls the environment/antagonist role and humans control agent characters. Primary example: Dungeon Keeper model (LLM = dungeon master spawning monsters/traps, humans = hero party). Resource tension on both sides is core to gameplay depth.

## Consequences

Five game formats identified: Dungeon Keeper vs Heroes, Civilization-Lite, Heist Planner vs Security Director, Ecosystem Architect (cooperative), Time Loop Detective. Dungeon Keeper is strongest starting point. LeWM world model integrated as potential physics backbone.
