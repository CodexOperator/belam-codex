---
primitive: lesson
status: active
severity: high
discovered: 2026-03-15
context: v4 pipeline — Critic→Builder sessions_send timeout
tags: [multi-agent, coordination, sessions-send, timeout]
---

# Lesson: sessions_send Timeouts — Use Filesystem-First Coordination

## What Happened
During v4 Phase 2, Critic used `sessions_send` to send detailed fix instructions (BLOCK-1 + BLOCK-2) to Builder. The message was delivered and Builder acted on it, but the Critic got `"status": "timeout"` back — it never received confirmation. Builder also timed out trying to ping Critic back. Both agents thought the other hadn't received their message.

## Root Cause
`sessions_send` with default `timeoutSeconds > 0` blocks the sender waiting for the target agent to **fully complete its run** (including all tool calls — file reads, code execution, git commits). Agent runs routinely take 30-120 seconds, exceeding the timeout window.

## Resolution
Adopted **filesystem-first coordination** protocol:
1. Write all data (designs, reviews, fixes) to shared files in `research/pipeline_builds/`
2. Use `sessions_send` with `timeoutSeconds: 0` (fire-and-forget) for notifications only
3. Reference file paths in pings, never put critical content in the message payload
4. Use group chat (`message` tool) for status updates visible to Shael

## Key Insight
The agents naturally evolved toward this pattern — when sessions_send failed, Critic wrote `v4_critic_phase2_blocks.md` to disk and Builder read it. The filesystem is a more reliable coordination layer than synchronous message passing for agents doing heavy work.
