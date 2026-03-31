---
primitive: lesson
date: 2026-03-23
source: session a1318751
confidence: high
upstream: [lm-entries-must-be-compelling-to-displace-raw-scripts]
downstream: []
tags: [instance:main, coordinate-system, codex-layer, lm, boot, scaffold]
promotion_status: promoted
doctrine_richness: 9
contradicts: []
---

# r0-scaffold-as-lightweight-coordinate-mode-nudge

## Context

Shael observed that the full codex-layer interceptor (t1) is heavy machinery. The LM exists as a menu, but agents still reach for raw shell commands because there's no behavioral framing establishing "coordinate mode is the expected interface."

## What Happened

Shael proposed using an R0 `--scaffold` flag at session boot (via cockpit plugin, `before_prompt_build`) to inject a compact header block that frames the session as "Coordinate Mode Active" — listing available coords and nudging toward them. This is lighter than a programmatic interceptor and can ship independently.

## Lesson

Prompt-level context framing ("you are in coordinate mode") shapes agent behavior more reliably and immediately than waiting for a full programmatic interceptor. A compact scaffold injection at boot is a viable Phase 0 before the full codex layer.

## Application

Implement via cockpit plugin injecting a coordinate grammar header on `before_prompt_build`. The LM provides the grammar; the scaffold provides the behavioral frame. This is now scoped as item 6 on t6 (lm-v2).
