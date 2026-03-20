---
primitive: decision
status: accepted
date: 2026-03-20
context: Phase 2 is human-directed — requires Shael's input before proceeding
alternatives: [file-based passive gate, no gate]
rationale: Explicit approval is clearest; one command bundles approval + direction
consequences: [pipelines pause at local_analysis_complete, autorun never touches Phase 2]
tags: [pipeline, gate, phase2, infrastructure]
upstream: [memory/2026-03-17_134119_major-session-built-three-infrastructure]
---

# Phase 2 Requires Explicit Human Approval

## Context

Pipelines follow: Phase 1 (autonomous build) → local experiments → local analysis → Phase 2 (human-in-the-loop). Phase 2 requires Shael's direction — what to investigate, what to prioritize. Without a gate, the orchestrator auto-advanced from `local_analysis_complete` directly into Phase 2 architect design with no human input.

## Options Considered

- **Explicit kickoff command** (chosen): `belam kickoff <ver> --phase2 --direction <file>` — human runs command to approve + attach direction
- **File-based passive gate:** autorun detects `{version}_phase2_shael_direction.md` and auto-kicks. More moving pieces, less explicit.
- **No gate:** auto-transition straight through. Phase 2 is fundamentally human-directed — wrong approach.

## Decision

`local_analysis_complete` is a terminal stage with no auto-transition in `STAGE_TRANSITIONS`. Phase 2 requires:

```
belam kickoff <ver> --phase2 [--direction <file>]
```

The `--direction` flag copies Shael's direction file to `pipeline_builds/{version}_phase2_shael_direction.md` for the architect. The orchestrator sends a notification when a pipeline reaches this gate.

## Consequences

- Pipelines pause at `local_analysis_complete` until Shael approves
- Direction context is bundled at kickoff time — one action, not two
- Autorun never touches Phase 2 transitions — fully human-controlled
- Architect always has direction file in standard location when Phase 2 starts
