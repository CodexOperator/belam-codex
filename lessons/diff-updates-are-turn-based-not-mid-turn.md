---
primitive: lesson
slug: diff-updates-are-turn-based-not-mid-turn
title: Diff Updates Are Turn-Based, Not Mid-Turn
importance: 3
tags: [instance:main, render-engine, diff, architecture, context]
created: 2026-03-23
promotion_status: exploratory
doctrine_richness: 4
contradicts: []
---

# Lesson: Diff Updates Are Turn-Based, Not Mid-Turn

## What Happened
Shael asked whether live diffs would show up mid-session. Clarification was needed on when exactly diffs appear.

## The Pattern
Diffs from the render engine are **turn-based**, not real-time push:

1. inotify fires → tree updates → diff recorded in engine RAM
2. Diffs **accumulate** between turns
3. On the **next turn** (next user message or heartbeat), cockpit's `before_prompt_build` queries `my_diff` via UDS
4. That turn's context includes all accumulated diffs since last query
5. There is no mid-turn push — coordinator can't see a diff that arrives while it's generating a response

## Why It Matters
- Coordinator should not expect to "see" changes while mid-response
- Diff-triggered heartbeats solve the "no one sent a message" gap, not the mid-turn gap
- The UDS anchor pattern ensures each session only gets diffs it hasn't seen yet

## Related
- upstream: codex-engine-v2-live-diff-architecture
- upstream: diff-triggered-heartbeat-architecture
