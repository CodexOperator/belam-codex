---
primitive: lesson
date: 2026-03-25
source: "Shael session: critic block session mode design"
confidence: high
project: snn-applied-finance
tags: [instance:main, orchestration, agents, git, handoff]
applies_to: [pipeline_orchestrate, handoff_diff, agent-context]
upstream: [decision/session-continuity-on-block-with-phase-diff]
promotion_status: exploratory
doctrine_richness: 10
contradicts: []
---

# Lesson: Per-Agent Git HEAD Enables Targeted Cross-Phase Diffs

## Pattern
Track a git HEAD snapshot per agent per pipeline. When the same agent returns in a later phase, give them a verbose diff between their last HEAD and current state — not a diff of the most recent turn.

## Why It Matters
Between phases, multiple other agents work, experiments run, and files change. An agent returning in phase 2 can't see what changed relative to their own prior work without a HEAD anchored to when *they* last completed a turn. Generic "last turn" diffs miss all the intervening work.

## Mechanics
1. **When agent completes a turn without being blocked** → snapshot HEAD (git hash) into `pipeline_state.json` as `agent_heads.<agent_name>`
2. **Blocks within a phase don't update HEAD** — the agent is in a `continue` session, so their context already spans the block cycle
3. **First turn of next phase** → generate diff from `agent_heads.<agent_name>` to current working state and include in handoff message
4. Reset HEAD at end of each completed (non-blocked) turn

## Why This Holds
The templates never call the same agent consecutively across phase boundaries — there's always intervening work by other agents or system stages. So the per-agent HEAD always represents a meaningful boundary: "everything that happened since I last touched this."
