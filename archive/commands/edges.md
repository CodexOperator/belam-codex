---
primitive: command
name: R edges
usage: "R edges [--check] [--fix]"
category: memory
alias: R eg
tags: [memory, edges, relationships]
---

## R edges

Checks recently added primitives for missing inter-instance edges (upstream/downstream links in YAML frontmatter).

### What it does

- Scans all primitives (tasks, decisions, lessons, knowledge, pipelines, projects) for frontmatter `upstream` and `downstream` fields.
- Identifies primitives that reference other primitives by slug but lack the corresponding reverse link.
- Reports gaps: e.g. task A lists decision B as upstream, but decision B has no downstream entry for task A.

### Flags

| Flag | Behavior |
|------|----------|
| _(none)_ | Print a summary of primitives with missing/asymmetric edges |
| `--check` | Detailed check mode — shows each primitive's edge state |
| `--fix` | Spawns a Sonnet subagent to add missing edges as atomic micro-commits |

### Usage

```bash
R edges           # summarize missing edges
R edges --check   # detailed report
R edges --fix     # auto-fix with subagent (micro-commits per primitive)
R eg              # alias
```

### --fix behavior

When `--fix` is passed, R edges spawns a `claude-sonnet` subagent with a focused prompt: given the list of missing edges, add the reverse links to each primitive's frontmatter and commit each fix as a small git commit (`git commit -m "edges: add reverse link for <slug>"`). This avoids accumulating stale edge debt.

### Notes

- Edges are how primitives know about each other across types (e.g. a `task` depends on a `decision`).
- Missing edges don't break the system but reduce graph traversal quality (e.g. **`R -g` won't show full connectivity).
- Run periodically during heartbeats or after creating a batch of new primitives.
