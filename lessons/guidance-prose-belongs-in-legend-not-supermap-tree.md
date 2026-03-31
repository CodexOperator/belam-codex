---
primitive: lesson
date: 2026-03-23
source: session d4c5a542 - R command guidance placement
confidence: high
upstream:
  - legendary-map-as-lm-namespace-on-supermap
downstream:
  - supermap-pure-signal-legend-as-orientation-layer
tags:
  - instance:main
  - supermap
  - lm
  - legend
  - r-command
  - design
importance: 3
promotion_status: candidate
doctrine_richness: 8
contradicts: []
---

# guidance-prose-belongs-in-legend-not-supermap-tree

## Context

R command was missing guidance on using the supermap with LM coordinates. Iteration explored embedding prose directly in the coordinate tree.

## What Happened

Initial fix embedded 3 lines of guidance prose inside `render_supermap()`, prepended to the coordinate tree using `│` prefix. This worked technically but mixed signal types — dense coordinate tree + prose instructions in the same block. Shael flagged this as potentially redundant given the legend already exists as an orientation block.

## Lesson

The supermap tree is pure signal — coordinates and structure. Prose guidance clutters the tree and dilutes its density. The legend is the natural orientation layer and the right single place for "how to use this" content.

## Application

- When adding any instructional or guidance text about the workspace: put it in `codex_legend.md`, not inline in the supermap
- `render_supermap()` should emit only coordinate tree structure
- The legend follows the supermap and acts as the "map key" — rich enough to orient an agent seeing the system for the first time
- Redundancy across multiple injection points (plugin + supermap + legend) is worse than one rich source
