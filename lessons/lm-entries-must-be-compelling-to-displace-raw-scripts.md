---
primitive: lesson
date: 2026-03-23
source: (add source)
confidence: high
upstream: []
downstream: []
tags: [instance:main, lm, coordinate-grammar, ux]
promotion_status: promoted
doctrine_richness: 8
contradicts: []
---

# lm-entries-must-be-compelling-to-displace-raw-scripts

## Context

Session 2026-03-23: Shael noticed that Belam bypassed the coordinate grammar entirely when launching a pipeline, despite having the full supermap + LM + legend block in context.

## What Happened

Even with LM and legend visible, the agent defaulted to raw scripts. Shael's question about using supermap commands surfaced this. The agent admitted the LM entries are too abstract ("render primitive", "{coord}") — they don't pattern-match fast enough to displace familiar script invocations. This was the exact motivation behind Phase 2 of codex-engine-v3-legendary-map: enrich LM descriptions with concrete examples like "t1 views task 1, d5 views decision 5, p2 views pipeline 2."

## Lesson

Abstract LM entry descriptions are insufficient — entries need concrete examples that pattern-match instinctively, or agents (including the main session) will default to raw scripts even when the coordinate grammar is available.

## Application

- LM entries should include inline examples, not just syntax placeholders
- Phase 2 direction: enrich description fields with the most useful concrete examples and formatting
- Test: would a fresh agent seeing this entry immediately know what to type? If not, it needs enrichment
