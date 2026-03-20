---
primitive: decision
status: proposed
date: 2026-03-20
context: Primitive relationship graph exists but is sparsely linked — need a way to discover and wire implicit relationships across ~100 primitives
alternatives: [single-pass-bulk-analysis, manual-linking-only, embedding-similarity]
rationale: Fresh context per batch preserves judgment quality; deterministic orchestration keeps token cost low; incremental progress is auditable
consequences: [knowledge-graph-densifies-over-days, canvas-visualization-becomes-useful, relationship-quality-depends-on-prompt-design]
upstream: [decision/primitive-relationship-graph, decision/clock-cycles-over-tokens]
downstream: [task/build-incremental-relationship-mapper]
tags: [infrastructure, knowledge-graph, primitives, relationships]
---

# Incremental Relationship Mapping via Pairwise Opus Comparison

## Context

The primitive relationship graph (`decisions/primitive-relationship-graph`) gives every primitive upstream/downstream fields, and `belam link` enables batch wiring. But with ~100 primitives, manually identifying all meaningful relationships is impractical. The implicit structure exists — earlier lessons inform later decisions, shared tags suggest connections — but it needs to be made explicit.

## Options Considered

- **Single-pass bulk analysis:** Feed all primitives to one large context, map everything at once. Fast but context pollution degrades quality for later comparisons. Attention is finite.
- **Manual linking only:** Wire relationships as they come up naturally. Slow, incomplete, but always high quality.
- **Embedding similarity:** Compute vector embeddings, link above threshold. Cheap but shallow — catches lexical similarity, misses conceptual relationships.
- **Incremental pairwise comparison:** Small batches with fresh Opus context each time. Slow but thorough, auditable, and judgment quality stays pristine.

## Decision

**Incremental pairwise comparison with fresh context per batch.** A deterministic orchestrator (`scripts/map_relationships.py`) tracks progress, pre-filters obvious non-matches, and spawns a fresh Opus reasoning subagent for each batch of 3-5 primitive pairs. The agent sees only those primitives' content, judges relationships, and outputs structured links. The orchestrator applies them via the `belam link` backend and marks pairs as processed.

Key design principles:
- **Clock cycles over tokens**: orchestration is pure Python, only genuine judgment uses LLM
- **Pristine context**: despawn and reset between batches — no accumulated state
- **Day-based temporal axis**: compare primitives within and across days, leveraging chronological ordering as implicit upstream/downstream scaffold
- **Pre-filtering**: tag overlap, shared projects, temporal proximity reduce the comparison matrix before any LLM touches it
- **Scheduling**: ~every 15 minutes when active, keeping per-hour token load light

## Consequences

- Knowledge graph densifies organically over ~2 weeks (full first pass)
- Canvas graph visualization becomes genuinely navigable as edges appear
- Quality depends heavily on the comparison prompt — needs careful design before activation
- Progress is resumable and auditable via `relationship_progress.json`
- Pre-filtering design determines both coverage and cost
