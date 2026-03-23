---
primitive: decision
slug: r-f-label-split-by-agent-role
title: R/F Label Split by Agent Role
importance: 4
tags: [instance:main, render-engine, diff, cockpit, context]
created: 2026-03-23
---

# Decision: R/F Label Split by Agent Role

## Context
The render engine produces two label types on diffs:
- **R labels**: rendered summary lines (compact, coordinate-level)
- **F labels**: full file content inline (`F[m1]: | --- | title: ...`)

Previously all agents received R-only labels. With F-label content now stored in DiffEntry, we can choose per-agent.

## Decision
- **Coordinator (main session)**: R-only diffs. Coordinator needs signal, not content — can `read` any entry that looks relevant.
- **Pipeline agents** (builder, analyst, etc.): R+F labels by default. These agents benefit from seeing full content of new primitives, experiment results, and file changes inline without extra reads.

## Rationale
- Coordinator context is precious — F-label content would flood it for every memory extraction
- Pipeline agents operate in isolated sessions with focused tasks; full content improves their accuracy
- Memory entries are compact enough that F-labels don't catastrophically blow up pipeline agent context
- Creates a natural experimentation axis: can tune which agents see full content vs summaries

## Implementation
Cockpit plugin (`index.ts`) detects agent role:
- main session → `include_content: false`
- pipeline/other → `include_content: true`

Render engine `my_diff` and `diff` commands respect `include_content` param.

## Related
- upstream: codex-cockpit-plugin-architecture
- upstream: codex-engine-v2-live-diff-architecture
- upstream: diff-triggered-heartbeat-architecture
