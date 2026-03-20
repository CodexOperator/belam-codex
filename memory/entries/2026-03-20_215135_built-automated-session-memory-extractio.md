---
primitive: memory_log
timestamp: "2026-03-20T21:51:35Z"
category: event
importance: 4
tags: [instance:main, memory-extraction, automation, bootstrap-hook, sessions-spawn]
source: "session"
content: "Built automated session memory extraction system. On /new or /reset, a hook writes a marker file and the agent spawns a subagent that parses the previous session JSONL, extracts memories/lessons/decisions, creates primitives with tags and edges, and commits. Components: extract_session_memory.sh (orchestrator), parse_session_transcript.py (JSONL→markdown), hooks/memory-extract/handler.ts (bootstrap hook), run_memory_extraction.py (orchestrator entrypoint). Session parser truncates to 40K chars for token efficiency. Subagent uses anthropic/claude-sonnet-4-6 model."
status: active
---

# Memory Entry

**2026-03-20T21:51:35Z** · `event` · importance 4/5

Built automated session memory extraction system. On /new or /reset, a hook writes a marker file and the agent spawns a subagent that parses the previous session JSONL, extracts memories/lessons/decisions, creates primitives with tags and edges, and commits. Components: extract_session_memory.sh (orchestrator), parse_session_transcript.py (JSONL→markdown), hooks/memory-extract/handler.ts (bootstrap hook), run_memory_extraction.py (orchestrator entrypoint). Session parser truncates to 40K chars for token efficiency. Subagent uses anthropic/claude-sonnet-4-6 model.

---
*Source: session*
*Tags: instance:main, memory-extraction, automation, bootstrap-hook, sessions-spawn*
