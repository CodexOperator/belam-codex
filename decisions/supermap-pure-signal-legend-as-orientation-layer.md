---
primitive: decision
status: accepted
date: 2026-03-23
context: supermap guidance placement iteration
alternatives:
  - inline guidance in supermap tree
  - guidance in cockpit plugin injection
  - guidance in render_supermap() function header
rationale: supermap should be dense coordinate signal; prose clutters the tree
consequences:
  - legend is now the single canonical orientation layer
  - all guidance maintained in one file (codex_legend.md)
  - render_supermap() stays prose-free
upstream:
  - legendary-map-as-lm-namespace-on-supermap
downstream: []
tags:
  - instance:main
  - supermap
  - lm
  - legend
  - r-command
importance: 3
---

# supermap-pure-signal-legend-as-orientation-layer

## Context

Shael noticed R command wasn't showing guidance on how to use the supermap with LM coordinates. Multiple placement approaches were attempted during a short session, raising the question of where guidance prose belongs.

## Options Considered

- **Option A:** Embed 3-line guidance in supermap tree header (in `render_supermap()`) — immediate but clutters coordinate signal with prose
- **Option B:** Place guidance in cockpit plugin injection layer — duplicates across consumers
- **Option C:** Supermap = pure tree, legend = identity + rich "How to Use" orientation section — single source, no tree pollution

## Decision

Supermap renders as pure coordinate tree (no inline prose). `codex_legend.md` is the single orientation layer: identity block + "How to Use the Supermap" section that teaches the LM as action grammar/chart.

## Consequences

- Every consumer that renders supermap + legend gets clean tree then rich guidance
- `render_supermap()` stays free of prose — coordinates only
- `codex_legend.md` is the canonical place to update agent orientation
- Gateway restart required for cockpit plugin cleanup to propagate
