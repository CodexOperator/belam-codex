---
primitive: decision
date: 2026-03-23
status: under-discussion
upstream: [codex-cockpit-plugin-architecture, codex-render-foreground-ram-tree, render-engine-as-default-context-layer]
downstream: []
tags: [instance:main, codex-engine, render, zoom, context-efficiency]
importance: 3
promotion_status: exploratory
doctrine_richness: 9
contradicts: []
---

# zoom-replaces-supermap-injection-option

## Decision

Three options identified for handling zoom context efficiency (R-labels are additive — zoom adds to context, doesn't replace supermap):

1. **R-label supersede tags** — zoom output includes `[supersedes R{n}]` hint; cheap/heuristic, no actual context reduction.
2. **Wire render engine diffs into cockpit** — cockpit plugin injects per-turn diff instead of full re-render; the real architectural fix (render engine UDS already built in v3 Phase 2 but not wired).
3. **Zoom replaces supermap injection** — when zoom is active, cockpit injects zoom content *instead of* supermap for that turn; reverts next turn without zoom.

## Rationale

Shael clarified that the supermap is injected fresh each turn via the cockpit plugin anyway (not accumulated from history), so the per-turn diff (option 2) only matters within a turn's output — the real duplication is the zoom output sitting alongside the supermap in context history. Option 3 is the cheapest real fix: conditional injection. Option 2 is deferred to a future pipeline phase.

## Status

Under discussion — session covered the architecture but a final implementation direction was not committed in the captured portion of the transcript.
