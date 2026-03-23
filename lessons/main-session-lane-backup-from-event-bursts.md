---
primitive: lesson
date: 2026-03-23
source: telegram-unresponsive debugging 2026-03-23
confidence: high
importance: 4
upstream: [diff-triggered-heartbeat-architecture]
downstream: []
tags: [instance:main, telegram, lane-queue, system-events, diff-trigger]
---

# main-session-lane-backup-from-event-bursts

## Context

Shael asked why Telegram wasn't responding. Multiple system events fired simultaneously:
exec failures, diff-trigger (10 F-label threshold), stall recovery SIGTERM — all queued into
the main session lane at once. Lane wait hit 299 seconds (nearly 5 minutes).

## What Happened

The main session has a single queue lane. When pipeline agents generate bursts of F-label
changes (architect → critic → builder can produce 10+ in minutes), the diff-trigger fires
and injects a wake event into the main session queue. Combined with exec failure events and
heartbeat crons, the lane backs up — blocking interactive Telegram DMs behind low-priority
system events.

## Lesson

Low diff-trigger thresholds (e.g., 10 F-labels) cause frequent main-session wake events that
compete with interactive messages, creating noticeable Telegram lag under normal pipeline load.

## Application

- Raise diff-trigger threshold from 10 → 25–30 F-labels to reduce wake frequency without
  losing signal (diffs accumulate and are delivered on next turn regardless).
- Long-term: interactive messages (Telegram DMs) need priority over system events — this
  requires OpenClaw-level priority lane support (file as feature request upstream).
- As a rule: diff-trigger thresholds should be set relative to expected agent write velocity,
  not an arbitrary small number.
