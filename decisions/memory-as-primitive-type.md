---
type: decision
title: "Decision: Memory Hierarchy as Primitive Type"
status: accepted
date: 2026-03-18
project: workspace-infrastructure
tags: [memory, primitives, hierarchy, infrastructure]
downstream: [memory/2026-03-18_235054_commands-and-skills-promoted-to-first-cl, memory/2026-03-19_005231_primitives-are-the-universal-organizatio, memory/2026-03-18_203356_memory-hierarchy-now-indexed-as-primitiv, memory/2026-03-18_215728_extended-memory-content-embed-to-include]
upstream: [decision/memory-as-index-not-store]
---

# Decision: Memory Hierarchy as Primitive Type

## Context

The workspace had two parallel indexing systems: primitives (lessons, decisions, tasks, projects) indexed via `embed_primitives.py` into boot context, and the hierarchical memory system (daily→weekly→monthly→quarterly→yearly) which lived in `memory/INDEX.md` but was never surfaced at boot time.

## Decision

Treat memory consolidation outputs (weekly and above) as a primitive type — same frontmatter convention, same auto-indexing, same structural presentation in boot files.

## Implementation

1. **Weekly/monthly/quarterly/yearly files get YAML frontmatter** with `type: memory`, `level:`, `period:`, `title:`, `tags:`, `entry_count:`, `generated:`
2. **`embed_primitives.py` extended** with `<!-- BEGIN:MEMORY_HIERARCHY -->` section in MEMORY.md showing topology: daily count/range, indexed entries count, and YAML index of all hierarchy files
3. **Daily logs stay raw** — they're working files, not consolidated knowledge
4. **Same porting path** — `sync_knowledge_repo.py` already captures memory; frontmatter makes it structurally first-class

## Why Separate Category

Memory primitives are temporal (time-indexed) rather than categorical (topic-indexed). They share the same shape (frontmatter + markdown body + tags) but their natural organization is chronological hierarchy, not flat directory. Keeping them as their own category preserves this while giving them the same indexing benefits.

## Alternatives Considered

- **No primitive treatment** — rejected; memory hierarchy was invisible at boot time
- **Mix into existing categories** — rejected; temporal vs categorical is a real structural difference
- **Full daily indexing** — rejected; dailies are working files, too noisy for boot context
