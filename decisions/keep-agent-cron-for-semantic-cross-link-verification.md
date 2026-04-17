---
primitive: decision
date: 2026-04-17
status: accepted
upstream: []
downstream: []
tags: [instance:main, memory, cron, verification, cross-links, automation]
promotion_status: candidate
doctrine_richness: 8
contradicts: []
---

# keep-agent-cron-for-semantic-cross-link-verification

## Decision

Keep the daily memory/primitives commit job as an agent cron, and make cross-link verification an explicit part of its prompt, instead of replacing it with a pure script.

## Context

A nightly job already existed to commit and push daily memory plus changed lesson/decision primitives. We considered replacing it with a plain script or system timer because the file selection and git operations are deterministic. But Shael wanted the job to also verify semantic quality — especially whether daily memory, lessons, and decisions were cross-linked cleanly.

## Options Considered

1. **Pure script/timer** — simpler, cheaper, and good for deterministic staging/commit/push only.
2. **Agent cron** — heavier, but able to inspect files semantically, spot obvious missing links, and report uncertainty.

## Decision Rationale

Mechanical git automation is script-friendly, but cross-link verification is semantic review work. That review benefits from an agent that can read the changed primitives together, make narrow high-confidence metadata/link fixes, and call out ambiguous gaps instead of blindly committing them.

## Consequences

- The cron remains agent-driven.
- The prompt must require mandatory cross-link verification before commit/push.
- The agent should stay conservative: fix only obvious omissions, avoid speculative relationships, and report remaining uncertainty.
- If the workflow ever shrinks back to purely mechanical staging and pushing, a script/timer can replace it later.
