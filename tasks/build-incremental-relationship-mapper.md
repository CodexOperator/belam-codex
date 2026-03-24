---
primitive: task
status: done
priority: medium
execution: standalone_cron
created: 2026-03-20
owner: belam
depends_on: [primitive-relationship-graph]
upstream: [decision/primitive-relationship-graph, decision/indexed-command-interface, memory/2026-03-20_033917_primitive-relationship-graph-deployed-al]
downstream: []
tags: [infrastructure, knowledge-graph, primitives, relationships]
---

# Build Incremental Relationship Mapper

## Description

Build a slow, incremental relationship mapper that compares primitives pairwise using an Opus reasoning model, wiring upstream/downstream links via `R link`. Designed to run in small batches (3-5 pairs per invocation) with fresh context each time — pristine attention over speed.

## Design Decisions (Pending)

- **Comparison scope:** Which primitive types to compare against which (lessons↔decisions is high-value, commands↔commands probably not)
- **Pre-filtering:** Tag overlap, temporal proximity, shared project refs — cheap heuristics to skip obviously unrelated pairs
- **Batch size:** 3-5 pairs per invocation (TBD based on testing)
- **Scheduling:** Every 15 min via cron/heartbeat (not activated until design is finalized)
- **Prompt design:** The comparison prompt is where quality lives — needs careful crafting
- **Day-based vs type-based:** Shael suggested day-by-day pairwise comparison as one axis; type-within-day as another

## Architecture

1. `scripts/map_relationships.py` — deterministic orchestrator
2. `canvas/relationship_progress.json` — tracks completed pairs
3. Spawns one Opus subagent per batch with only the relevant primitive content
4. Agent outputs structured relationship judgments
5. Script applies via `R link` backend (direct Python, no shell)
6. Smart filtering reduces C(100,2) ≈ 4,950 pairs to meaningful subset

## Acceptance Criteria

- [ ] `scripts/map_relationships.py` exists and runs standalone
- [ ] Progress tracking persists across invocations
- [ ] Pre-filtering reduces comparison matrix to meaningful pairs
- [ ] Each invocation spawns fresh Opus context (no accumulated state)
- [ ] Relationships applied via existing `R link` backend
- [ ] Dry-run mode for testing without writes
- [ ] Design decisions above resolved with Shael before cron activation

## Notes

- Clock cycles over tokens: orchestration is deterministic, only judgment uses LLM
- Full first pass at 4 pairs/15min ≈ 13 days for 4,950 pairs (before filtering)
- Canvas graph visualization (`canvas/graph.html`) shows results in real-time
