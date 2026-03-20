---
primitive: decision
status: accepted
date: 2026-03-19
context: LLM tokens cost orders of magnitude more than CPU cycles
alternatives: [LLM-driven heartbeat decisions]
rationale: Every deterministic operation should be code, not reasoning
consequences: [belam CLI and autorun scripts are the right pattern, continuously migrate]
tags: [infrastructure, cost, design-principle, tokens]
---

# Clock Cycles Over Tokens

## Context

Design principle from Shael (2026-03-19): clock cycles are cheaper than tokens by incomprehensible orders of magnitude. Heartbeat tasks, primitive edits, pipeline management, and file operations were all consuming LLM reasoning tokens for work that could be deterministic scripts.

## Decision

Every operation that can be done via script/CLI instead of LLM reasoning should be. The `belam` CLI and `pipeline_autorun.py` are the right pattern. Continuously migrate LLM-decision work to deterministic code wherever judgment isn't genuinely needed.

**Use LLM tokens for:**
- Genuine judgment calls (design decisions, code review, analysis)
- Creative work (architecture, hypothesis generation)
- Human communication

**Use clock cycles for:**
- Pipeline stage transitions
- File operations and primitive edits
- Gate checking and stall detection
- Memory consolidation and embedding
- Git commits and exports

## Consequences

- Heartbeat tasks are script-first, LLM-second
- New automation always starts as a script, not an agent task
- Agent tokens reserved for work that genuinely requires reasoning
