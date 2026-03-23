---
primitive: decision
date: 2026-03-23
status: active
decider: shael+belam
upstream: [legendary-map-as-lm-namespace-on-supermap, lm-design-tool-patterns-navigable-runnable, r0-scaffold-as-lightweight-coordinate-mode-nudge]
downstream: []
tags: [instance:main, lm, infrastructure, coordinate-system, scaffold]
---

# lm-v2-task-coordinate-native-launch-and-scaffold

## Decision

Create t6 (lm-v2-coordinate-native-pipeline-launch-and-workflow-enrichment) as a high-priority infrastructure task. Scope includes:
1. Coordinate-native pipeline launch (`e0 t{n}` syntax)
2. Concrete workflow step documentation (replace alias references with real script paths)
3. Pipeline lifecycle coordinate commands (archive, block, resume)
4. Richer task-pipeline linking in LM display
5. Improved LM entry descriptions
6. R0 `--scaffold` boot injection via cockpit plugin for coordinate-mode framing

## Rationale

LM v1 (codex-engine-v3-legendary-map) delivered the grammar. v2 closes the gap between "grammar exists" and "agents live in it natively." The scaffold (item 6) was added because it can ship independently as a lightweight behavioral nudge before the full codex-layer interceptor (t1) is ready.

## Alternatives Considered

- Fold items into t1 (codex-layer-v1): t1 is already scoped as a programmatic interceptor; mixing prompt-level scaffold into it blurs the boundary.
- Ship scaffold separately as its own task: valid, but the scope overlap with LM v2 makes co-location cleaner.

## Consequences

t6 pipeline active as of 2026-03-23. When delivered, agents will reach for `e0 t{n}` naturally at session start rather than falling back to raw script invocations.
