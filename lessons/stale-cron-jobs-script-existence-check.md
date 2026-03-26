---
primitive: lesson
date: 2026-03-26
source: main session — cron cleanup
confidence: high
upstream: []
downstream: []
tags: [instance:main, cron, infrastructure, maintenance]
---

# stale-cron-jobs-script-existence-check

## Context

Multiple cron jobs existed in the scheduler pointing to scripts that had been deleted as part of a memory system redesign (consolidate_memories.py, daily_agent_memory.py, weekly_knowledge_sync.py). The crons remained enabled=False but were never cleaned up.

## What Happened

When trying to re-enable memory consolidation crons, discovered all five existing jobs referenced scripts that no longer existed on disk. The old scripts had been retired as part of the memory-extraction-lessons-decisions-only decision (2026-03-25). Three replacement crons were created using surviving scripts (memory_weekly_consolidation.py, memory_monthly_consolidation.py, export_agent_conversations.py).

## Lesson

Cron jobs are not automatically invalidated when their target scripts are deleted. When retiring or redesigning scripts, explicitly clean up or update any cron jobs that depend on them. Stale crons accumulate silently.

## Application

When removing any script that cron jobs reference: immediately update or delete those cron entries. Before re-enabling disabled crons, verify target scripts still exist on disk.
