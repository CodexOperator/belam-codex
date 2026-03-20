---
primitive: decision
status: accepted
date: 2026-03-20
context: Primitives exist in isolation — no way to trace how lessons led to decisions, decisions spawned tasks, or memories crystallized into lessons
alternatives: [flat tags only, explicit link files, frontmatter relationship fields]
rationale: Frontmatter fields are the simplest approach — no new infrastructure needed, just two directional fields that create typed edges between primitives. The audit system can validate links and the index can render them.
consequences: [primitives become a navigable graph, audit can detect orphaned/broken links, belam can show upstream/downstream in detail views]
upstream: [decisions/indexed-command-interface]
downstream: [memory/2026-03-20_033917_primitive-relationship-graph-deployed-al]
tags: [infrastructure, primitives, knowledge-graph, conventions]
---

# Primitive Relationship Graph

## Design

Two new frontmatter fields on all primitive types:

### `upstream:` — What informed this primitive
Sources, inspirations, prerequisites. "This exists because of those."

```yaml
upstream: [decisions/clock-cycles-over-tokens, lessons/snn-treats-like-weird-cnn]
```

### `downstream:` — What this primitive led to
Consequences, follow-ups, spawned work. "This led to those."

```yaml
downstream: [tasks/setup-vectorbt-nautilus-pipeline, decisions/two-phase-backtest-workflow]
```

## Format

References use `type/slug` notation:
- `decisions/clock-cycles-over-tokens`
- `lessons/checkpoint-and-resume-pattern`
- `tasks/build-equilibrium-snn`
- `projects/snn-applied-finance`
- `memory/entries/2026-03-20_some-entry`

## Relationship Types

The direction encodes the relationship:
- **lesson → decision**: "This lesson informed this decision"
- **decision → task**: "This decision spawned this task"
- **memory → lesson**: "This observation crystallized into this lesson"
- **decision → decision**: "This decision led to this one"
- **lesson → lesson**: "This finding refined/extended this one"

The `supersedes` field remains separate — that's replacement, not connection.

## Rendering

`belam` detail views show upstream/downstream when present:
```
  ▴ upstream:   decisions/clock-cycles-over-tokens, lessons/snn-treats-like-weird-cnn
  ▾ downstream: tasks/setup-vectorbt-nautilus-pipeline
```

## Audit Integration

`belam audit` checks:
- Broken links (referenced primitive doesn't exist)
- Asymmetric links (A lists B as downstream, but B doesn't list A as upstream) — warning, not error
- Orphaned primitives (no upstream or downstream) — informational

## Progressive Population

Don't backfill everything at once. Add links as primitives are created or edited. Over time the graph fills in organically.
