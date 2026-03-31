---
primitive: decision
status: accepted
date: 2026-03-23
context: (add context)
alternatives: []
rationale: (add rationale)
consequences: []
upstream: [lesson/heartbeat-md-contaminates-manual-session-behavior]
downstream: []
tags: [instance:main, heartbeat, lm, coordinate-grammar, pipeline]
promotion_status: promoted
doctrine_richness: 9
contradicts: []
---

# heartbeat-md-e0-primary-path

## Context

2026-03-23: Shael caught Belam using raw `python3 scripts/...` invocations instead of `e0`/`R kickoff` during a manual pipeline launch. Investigation traced this to HEARTBEAT.md and launch-pipeline SKILL.md both presenting raw scripts as the primary/preferred path.

## Options Considered

- **Option A:** Leave both files as-is, rely on richer LM entries (Phase 2) to correct behavior
- **Option B:** Update both HEARTBEAT.md and launch-pipeline SKILL.md to use e0/R as primary, scripts as fallback — fix the source of the habit directly

## Decision

Update HEARTBEAT.md and launch-pipeline SKILL.md to use `e0` sweep and `R kickoff`/`R pipeline` commands as the primary invocation paths. Raw `python3 scripts/...` commands move to "fallback if coordinate engine unavailable." Both files edited in the 2026-03-23 session.

## Consequences

- Agents reading HEARTBEAT.md or the launch skill will default to coordinate grammar first
- Script fallbacks remain documented for edge cases (engine not yet initialized, etc.)
- Needs to be maintained: any future edits to these docs should preserve e0/R primacy
