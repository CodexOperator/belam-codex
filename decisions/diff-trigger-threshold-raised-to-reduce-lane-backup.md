---
primitive: decision
date: 2026-03-23
status: proposed
decider: Shael + Belam
importance: 3
upstream: [diff-triggered-heartbeat-architecture, main-session-lane-backup-from-event-bursts]
downstream: []
tags: [instance:main, diff-trigger, heartbeat, telegram, lane-queue]
---

# diff-trigger-threshold-raised-to-reduce-lane-backup

## Decision

Raise the diff-triggered heartbeat threshold from 10 F-label changes to **25–30 F-label
changes** to reduce main session queue pressure.

## Context

At threshold=10, pipeline agent activity (architect → critic → builder design cycles) routinely
generates 10+ F-label changes in minutes, causing the diff-trigger to fire repeatedly. Combined
with exec failure events and heartbeat crons, the main session lane backs up and Telegram DMs
experience multi-minute delays. The threshold of 10 was set arbitrarily during initial rollout.

## Rationale

- Diffs accumulate and are delivered in full on the next triggered turn — no signal is lost
  by waiting longer.
- Raising to 25–30 matches expected agent write velocity more closely (full architect design
  cycle is ~15–25 files).
- This is achievable immediately with zero infrastructure changes; we control the threshold.
- The longer-term fix (priority lanes for interactive messages) requires upstream OpenClaw work.

## Alternatives Considered

1. **Priority lanes** — Telegram DMs get priority over system events. Not currently supported
   by OpenClaw; filed as a wish.
2. **Keep threshold at 10** — Status quo; causes Telegram lag under normal pipeline load.

## Status

Proposed during 2026-03-23 session. Shael to confirm before implementation.
