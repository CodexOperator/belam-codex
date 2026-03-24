---
primitive: task
status: done
priority: medium
project: multi-agent-infrastructure
depends_on: []
tags: [research, infrastructure, spacetimedb, temporal, gaming]
pipeline: temporal-interaction-llm-gaming
created: 2026-03-21
---

# Temporal Interaction Layer & LLM-Native Gaming Foundation

## Description
Design and prototype a daemon-free temporal interaction system for LLM agents using:
1. SpacetimeDB (or equivalent temporal datastore) for shared world state with temporal subscriptions
2. OpenClaw `before_prompt_build` hooks for state delta injection (agent perceives time through diffs)
3. Agent actions writing back to temporal store, completing the loop

## Why This Matters
- Eliminates the need for daemon processes to give agents temporal awareness
- Enables the first LLM-native gaming layer: shared world state, separate render engines, unified temporal resolution
- Players (human or LLM) interact through temporal state diffs — true asynchronous multiplayer
- Builds on research-openclaw-internals pipeline's hook architecture findings

## Key Questions
- SpacetimeDB vs alternatives (SurrealDB, EventStoreDB) for our use case
- Can we achieve sub-second temporal resolution through hooks alone?
- What's the minimal viable shared world state schema?
- How do render engines (LLM text vs human visual) converge on the same world state?

## Related
- `tasks/codex-engine-v2-modes-mcp-temporal.md` — shared SpacetimeDB eval, .codex sync, persistent agents

## Artifacts
- Research from: research-openclaw-internals pipeline (hook architecture, plugin system)
- SpacetimeDB: https://spacetimedb.com

## Acceptance Criteria
- [ ] Working prototype: 2 agents sharing temporal state without a daemon
- [ ] State injection via before_prompt_build hook with temporal diffs
- [ ] Design doc for LLM-native gaming layer architecture
