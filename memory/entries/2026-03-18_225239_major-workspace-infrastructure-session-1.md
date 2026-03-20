---
primitive: memory_log
timestamp: "2026-03-18T22:52:39Z"
category: preference
importance: 4
tags: [infrastructure, cli, primitives, optimization]
source: "session"
content: "Major workspace infrastructure session: (1) Optimized embed_primitives.py — YAML→ASCII tree format for primitive index (39% smaller) and memory hierarchy (49% smaller). (2) Stripped embedded memory content from MEMORY.md system prompt — saves ~5,200 tokens per boot (agents read daily files on-demand instead). MEMORY.md went from 31K→7.2K chars. (3) Added trigger_embed.py with 5s debounce — wired into log_memory, consolidate_memories, weekly/monthly consolidation. Indexes auto-update on every write. (4) Built belam create CLI — 'belam create lesson/decision/task/project/skill' with proper frontmatter scaffolding, auto-triggers embed. Skill creation auto-generates both SKILL.md and decision primitive (skill-primitive-pairing convention). (5) Built belam edit CLI — fuzzy-match primitives, --set key=value for frontmatter updates, auto-triggers embed. (6) Created projects/agent-roster.md — single source of truth for all 4 agents (coordinator/architect/critic/builder), models, workspaces, sessions, conventions."
status: consolidated
upstream: [decision/memory-as-index-not-store]
---

# Memory Entry

**2026-03-18T22:52:39Z** · `preference` · importance 4/5

Major workspace infrastructure session: (1) Optimized embed_primitives.py — YAML→ASCII tree format for primitive index (39% smaller) and memory hierarchy (49% smaller). (2) Stripped embedded memory content from MEMORY.md system prompt — saves ~5,200 tokens per boot (agents read daily files on-demand instead). MEMORY.md went from 31K→7.2K chars. (3) Added trigger_embed.py with 5s debounce — wired into log_memory, consolidate_memories, weekly/monthly consolidation. Indexes auto-update on every write. (4) Built belam create CLI — 'belam create lesson/decision/task/project/skill' with proper frontmatter scaffolding, auto-triggers embed. Skill creation auto-generates both SKILL.md and decision primitive (skill-primitive-pairing convention). (5) Built belam edit CLI — fuzzy-match primitives, --set key=value for frontmatter updates, auto-triggers embed. (6) Created projects/agent-roster.md — single source of truth for all 4 agents (coordinator/architect/critic/builder), models, workspaces, sessions, conventions.

---
*Source: session*
*Tags: infrastructure, cli, primitives, optimization*
