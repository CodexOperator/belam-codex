---
primitive: lesson
date: 2026-03-23
source: p1 deliverable verification session
confidence: confirmed
upstream: [codex-engine-v2-dense-alphanumeric-grammar, legendary-map-as-lm-namespace-on-supermap]
downstream: []
tags: [instance:main, codex-engine, lm, bug, regex]
importance: 3
---

# is-coordinate-single-char-prefix-limitation

## Context

During p1 verification of codex-engine-v3-legendary-map, zooming to `lm6` or `lm` (expanded) silently failed with exit code 2. The LM namespace rendered correctly in the supermap but individual LM coordinate navigation was broken.

## What Happened

`is_coordinate()` in `codex_engine.py` used the regex `^(md|mw|[a-z])(\d+)?` — the `[a-z]` branch only matches a **single character**. The `lm` prefix is 2 characters and not explicitly listed alongside `md`/`mw`. So `lm6`, `lm`, and any `lm{N}` coordinate failed the gatekeeper check and fell through to `sys.exit(2)`. The coordinate *resolver* regex elsewhere used `[a-z]+` (multi-char), so the underlying data path worked — only the routing gate was broken.

## Lesson

`is_coordinate()` must list all multi-char namespace prefixes explicitly (or use `[a-z]+`), otherwise any new 2+ char prefix silently fails navigation.

## Application

Whenever a new multi-character namespace prefix is added to the engine, verify `is_coordinate()` handles it. The fix: add `lm` explicitly alongside `md`/`mw`, or change the single-char branch to `[a-z]+` globally (with exclusions for e0-e3 still in place). Committed fix in 68feb520.
