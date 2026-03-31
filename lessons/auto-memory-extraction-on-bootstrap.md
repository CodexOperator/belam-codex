---
primitive: lesson
date: 2026-03-20
source: session a6677470-aa48-4e7a-a298-e06f289140b0
confidence: high
upstream: []
downstream: []
tags: [instance:main, memory-extraction, bootstrap-hook, automation]
promotion_status: candidate
doctrine_richness: 9
contradicts: []
---

# auto-memory-extraction-on-bootstrap

## Context

Building an automated system to extract memories/lessons/decisions from sessions on every `/new` or `/reset`. The goal: replace manual memory consolidation with a hook-triggered subagent pipeline.

## What Happened

Tried spawning an extraction subagent directly from the `agent:bootstrap` hook handler. Failed — the hook fires while the new session already holds the JSONL file lock. Also discovered that `openclaw agent --agent main` with any `--session-id` still collides with the active session lock.

Also discovered that raw JSONL session files balloon to 200KB+ because tool results (file reads, etc.) get stored as full text blocks. The inline Python parser in bash grew too complex — extracted to `parse_session_transcript.py`.

## Lesson

**Hook → marker file → agent reads on boot → `sessions_spawn`** is the correct pattern. The hook cannot directly spawn a session for the same agent it's bootstrapping; it must defer to the agent itself.

## Application

- When the hook fires on `agent:bootstrap`, write a marker file (e.g. `memory/pending_extraction.json`) with the previous session path, instance name, and persona
- On session startup (AGENTS.md protocol), the agent checks for `pending_extraction.json`, spawns a subagent via `sessions_spawn`, then deletes the marker
- JSONL parser must truncate text blocks to ~500 chars and cap total transcript at ~40K chars (~10K tokens) for subagent efficiency
- Model alias for subagent spawns: `anthropic/claude-sonnet-4-6` (not `anthropic/claude-sonnet-4-20250514`)
- Extract complex inline Python from bash scripts into dedicated `.py` files early — bash+python hybrids get unmaintainable fast
