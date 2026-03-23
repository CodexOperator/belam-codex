---
primitive: lesson
date: 2026-03-23
source: p1 deliverable verification session
confidence: confirmed
upstream: [codex-engine-v2-dense-alphanumeric-grammar, lm-design-tool-patterns-navigable-runnable]
downstream: []
tags: [instance:main, codex-engine, lm, dot-syntax, dispatch, bug]
importance: 3
---

# dot-syntax-lN-workflow-dispatch-unreachable

## Context

After fixing `is_coordinate()`, dot-syntax sub-index lookups like `e0.l1` and `e1.l2` still failed with exit code 2. These are the workflow step listings embedded inside LM entries (e.g. "Full Pipeline Launch" steps).

## What Happened

`e0.l1` fell through all routing gates:
- **Not a V2 op**: `_V2_OP_START_RE = r'^e[0-3]([a-z]|$)'` — requires a letter or end after the mode digit; `.` doesn't match.
- **Not a coordinate**: `is_coordinate()` correctly rejects it (contains `.`).
- The dot-syntax handler that strips `.1` for JSON output only checks `dot_parts[1].isdigit()` — `l1` is not a digit, so it's skipped too.
- Result: nothing matched → `sys.exit(2)`.

The `resolve_workflow()` function existed and worked correctly — it just had no routing path to reach it.

## Lesson

`{coord}.l{N}` dot-syntax for workflow sub-indices needs its own early-intercept dispatch before both the V2 op detection and coordinate gatekeeper, since it matches neither pattern.

## Application

When adding dot-syntax variants to the command grammar, verify each variant hits a handler. Pattern `{alpha+digits}.l{N}` is now intercepted early via a dedicated block before V2 detection. Any future dot-syntax extensions should follow the same pattern: add a named intercept block rather than relying on existing gates to absorb novel syntax. Committed fix in 68feb520.
