---
title: "R link"
command: "R link <expr>..."
aliases: ["R ln"]
category: primitives
tags: [link, relationships, primitives, graph]
upstream: [decisions/indexed-command-interface, decisions/primitive-relationship-graph]
---

# R link

Wire upstream/downstream relationships between primitives using the indexed coordinate system.

## Syntax

```
R link <expr> [<expr> ...]
```

Each `<expr>` is a relationship expression:
- `a>b` — a's downstream includes b, b's upstream includes a
- `a<b` — b's downstream includes a, a's upstream includes b

Multiple expressions can be chained in a single call:
```
R link l4>d7 d7>t2 l8<p1
```

## Coordinate Types

| Prefix | Type      | Example |
|--------|-----------|---------|
| `l`    | lesson    | `l4`    |
| `d`    | decision  | `d7`    |
| `t`    | task      | `t2`    |
| `p`    | pipeline  | `p1`    |
| `pj`   | project   | `pj3`   |
| `k`    | knowledge | `k2`    |
| (bare) | last list | `4`     |

Bare numbers resolve against `~/.belam_last_context` (the most recent `R lessons`, `R decisions`, etc.).

## Examples

```bash
# Populate context first
R lessons

# Link lesson 1 to decision 1
R link l1>d1

# Link multiple relationships at once
R link l4>d7 d7>t2 l8<p1

# Using bare numbers (after running R lessons)
R link 1>d3
```

## Behavior

- Resolves coordinates to primitive file paths
- Reads existing `upstream`/`downstream` frontmatter lists
- Appends new entries (no duplicates)
- Writes both files atomically
- Runs `embed_primitives.py` once at the end to rebuild indexes
- Prints a summary of what was linked / skipped

## Notes

- Idempotent: running the same link twice is safe — duplicates are skipped
- The `>` and `<` operators mirror git-style direction arrows
- Alias: `R ln` works identically to `R link`
