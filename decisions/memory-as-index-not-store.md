---
primitive: decision
status: accepted
date: 2026-03-18
context: "MEMORY.md was a 186-line curated narrative duplicating content from primitives (lessons, decisions, daily logs). Redundant and hard to maintain."
alternatives: ["Keep MEMORY.md as full narrative (old approach)", "Kill MEMORY.md entirely, rely on memory_search + primitives", "Replace with lean boot index pointing to primitives (chosen)"]
rationale: Index primes the agent to use the primitive system for all knowledge retrieval. Eliminates duplication. 48 lines vs 186. Cold-start orientation preserved via pointers.
consequences: ["Agent must use memory_search and read primitives for detailed context", "No more manual MEMORY.md maintenance — just update pointers when new primitives are created", "Primitives become the canonical knowledge store"]
project: snn-applied-finance
tags: [infrastructure, memory, primitives]
downstream: [memory/2026-03-18_225239_major-workspace-infrastructure-session-1, memory/2026-03-19_005231_primitives-are-the-universal-organizatio, decision/memory-as-primitive-type, memory/2026-03-18_200633_built-embed-primitivespy-auto-generates, memory/2026-03-18_203356_memory-hierarchy-now-indexed-as-primitiv, task/build-codex-engine, decision/codex-engine-v1-architecture]
---

# Decision: MEMORY.md as Boot Index, Not Knowledge Store

MEMORY.md is now a 48-line orientation file containing only references to primitives and instructions for self-orientation. All actual knowledge lives in the structured primitive system (lessons, decisions, daily logs, tasks, projects).
