---
primitive: goal
status: active
priority: medium
created: 2026-03-23
owner: belam
tags: [codex, architecture, vision, long-term]
---

# Codex as Universal Navigation System

## Vision

The coordinate system grows downward from high-level workflows to fine-grained function calls, eventually terminating at assembly-level operations — then loops back up through itself until top-level branches become effective multi-stage execution pipelines.

Instead of writing code, you navigate a map of workflows.

## The Fractal Property

```
e0              → orchestration sweep (high-level)
e0.l1           → first complex e0 workflow
e0.l1.step3     → third step of that workflow  
e0.l1.step3.fn  → the actual function call
...eventually...
e0.l1.step3.fn.asm → the assembly instruction
```

Each level is navigable, inspectable, and executable. The map IS the program.

## What This Means

- No separate "code" and "documentation" — the coordinate tree is both
- Debugging = navigating to the coordinate where behavior diverges from intent
- Refactoring = restructuring the coordinate tree
- The LM at each level describes what's below it — recursive self-description all the way down

## Milestones

1. LM v1: action grammar for codex engine (current work)
2. LM v2: workflow compositions with sub-indices
3. LM v3: function-level coordinate mapping
4. LM v4: full program representation as navigable tree
