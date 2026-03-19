---
primitive: decision
status: accepted
date: 2026-03-19
context: Conflicting lessons (gpu-parallel-thrashing-t4 vs tiny-snn-gpu-parallelism) showed that outdated primitives in the boot index waste tokens and risk agents following stale advice
alternatives:
  - Delete superseded files entirely (loses searchability and audit trail)
  - Move to archive/ directory (adds directory complexity, breaks existing paths)
  - Add warning banner only (still wastes boot tokens)
rationale: Status field filtering reuses existing patterns (like archived pipelines) and keeps files discoverable via memory_search while removing them from expensive boot context
consequences:
  - Superseded primitives no longer appear in AGENTS.md or MEMORY.md boot indexes
  - Files remain in their original directory, searchable via memory_search
  - MEMORY.md tree shows count with "(+N archived/superseded)" suffix for transparency
  - Pattern applies to any primitive type, not just lessons
tags: [primitives, conventions, lifecycle, boot-optimization]
---

# Superseded Primitive Lifecycle

## Decision

When a primitive is replaced by a newer, more accurate one:

1. **Add `status: superseded` to the old primitive's frontmatter**
2. **Add `superseded_by: <new-primitive-id>` to the old primitive**
3. **Add `supersedes: <old-primitive-id>` to the new primitive**
4. **The old file stays in place** — same directory, same filename

## Behavior

- `embed_primitives.py` filters `status: superseded` (and `archived`) from both AGENTS.md and MEMORY.md boot indexes
- MEMORY.md tree shows the hidden count: `lessons/ (12)  (+1 archived/superseded)`
- Files remain fully discoverable via `memory_search` — the content and cross-references are preserved
- Agents following a `superseded_by` link always land on the current authoritative version

## When to Use

- A lesson is corrected by later findings (e.g., benchmarked data overrides theoretical advice)
- A decision is reversed or replaced by a new architectural choice
- Any primitive where the original content could mislead if read without the correction

## When NOT to Use

- Incremental updates — just edit the primitive directly
- Complementary information — use `related` field instead
- Temporary holds — use `status: paused` or similar
