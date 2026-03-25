---
primitive: lesson
date: 2026-03-25
source: templates pt namespace wiring session
confidence: confirmed
upstream: [templates-directory-as-pt-namespace, is-coordinate-single-char-prefix-limitation]
downstream: []
tags: [instance:main, codex-engine, templates, pipelines]
importance: 3
---

# pipeline-templates-hardcoded-dict-vs-dynamic-namespace

## Context

`e0 t1.pt1` syntax was already in the engine parser, but `PIPELINE_TEMPLATES` was a hardcoded dict `{1: 'builder-first', 2: 'research'}`. Adding a new template type required editing the engine source.

## What Happened

When wiring `templates/` as a proper `pt` namespace, we discovered the parser already handled `t{n}.pt{n}` coordinates — but the resolution step was a static lookup. Making it dynamic (scanning `get_primitives('pt')` at resolve time) required no grammar changes, only the lookup logic.

## Lesson

When a namespace is promoted to first-class coordinates, any hardcoded index maps that reference it should be replaced with dynamic namespace lookups (`get_primitives(prefix)`). The pattern: static dict → dynamic scan.

## Application

Applies to any engine feature that enumerates named items by integer index. If those items live in a namespace directory, use `get_primitives()` instead of maintaining a parallel dict. New entries become automatically addressable without code changes.
