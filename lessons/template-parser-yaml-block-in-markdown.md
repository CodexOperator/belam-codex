---
primitive: lesson
date: 2026-03-25
source: session:6b7bd235
confidence: high
importance: 3
upstream: [builder-first-pipeline-template-pattern]
downstream: [template-aware-pipeline-orchestration]
tags: [instance:main, pipelines, templates, patterns, infrastructure]
promotion_status: promoted
doctrine_richness: 8
contradicts: []
---

# template-parser-yaml-block-in-markdown

## Context

Building template-aware orchestration that reads pipeline transition maps from `templates/*.md` files.

## What Happened

Both `builder-first-pipeline.md` and `research-pipeline.md` already had a `## Stage Transitions` section with a fenced YAML block containing `first_agent`, `pipeline_fields`, and `transitions` keys. The builder wrote `template_parser.py` to parse these blocks with PyYAML + a regex fallback for edge cases with commas inside quoted strings.

## Lesson

Pipeline templates can double as machine-readable specs by embedding a fenced YAML block under a known heading (e.g. `## Stage Transitions`). Template docs stay human-readable while becoming directly parseable by orchestration code. No separate YAML sidecar files needed.

## Application

When designing agent-facing template documents that also need to be machine-readable, embed a clearly-delimited YAML block under a stable heading rather than creating parallel sidecar files. This keeps the authoritative spec co-located with the human explanation.
