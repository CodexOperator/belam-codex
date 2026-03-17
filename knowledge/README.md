# Knowledge Graph

*The workspace knowledge base — distilled patterns, technical findings, and cross-linked insights.*

## Structure

Each file in this directory is a **knowledge topic** — a living document that accumulates findings from:
- Memory entries (via `memory_daily_linker.py`)
- Weekly consolidations (via `memory_weekly_consolidation.py`)
- Lessons learned (via `weekly_knowledge_sync.py`)

```
knowledge/
  README.md              ← You are here
  _index.md              ← Auto-generated: all topics, tags, counts
  _tags.md               ← Auto-generated: tag index
  _weekly_synthesis.md   ← Auto-generated: cross-agent weekly synthesis

  snn-architecture.md         ← SNN Architecture Patterns
  financial-encoding.md       ← Financial Data Encoding
  gpu-optimization.md         ← GPU & Compute Optimization
  agent-coordination.md       ← Agent Coordination Patterns
  experiment-methodology.md   ← Experiment Methodology
  ml-architecture.md          ← ML Architecture Patterns
  research-workflow.md        ← Research Workflow
```

## File Format

Each topic file has:
```yaml
---
topic: Topic Name
tags: [tag1, tag2, ...]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [path/to/source, ...]
related: [other-topic-slug, ...]
---

# Topic Name

## Key Findings

- Finding 1 *(source: ...)*
- Finding 2 *(source: ...)*

## Notes

Contextual notes added manually or by the memory system.

## See Also

- [→ Daily YYYY-MM-DD](../memory/YYYY-MM-DD.md)
- [→ Weekly YYYY-WNN](../memory/weekly/YYYY-WNN.md)
```

## Cross-Linking

Links flow **upward** (daily → weekly → monthly → quarterly → yearly) and **sideways** (daily ↔ wiki, weekly ↔ wiki).

The memory system prefers linking to higher-level summaries in wiki pages:
- Quarterly > Monthly > Weekly > Daily

## Navigation

- Browse by topic: see `_index.md`
- Browse by tag: see `_tags.md`
- Memory hierarchy: `memory/INDEX.md`
- Source entries: `memory/entries/`

## Maintenance

- **Automatic**: Weekly sync runs every Monday at 03:00 UTC
- **Manual**: Add notes to the `## Notes` section of any topic file
- **Never delete** key findings — add context or mark them as outdated with a note

---

*Part of the Belam workspace memory system. See `scripts/weekly_knowledge_sync.py` for the sync logic.*
