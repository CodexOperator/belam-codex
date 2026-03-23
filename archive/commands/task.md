---
primitive: command
command: "R task <name>"
aliases: []
description: "Show one task (fuzzy match)"
category: primitives
tags: [task, detail, fuzzy-match]
status: superseded
superseded_by: decision/codex-engine-v1-architecture
---

# R task

Shows details for a single task, using fuzzy matching on the name. Use when you need the full context of a specific task including dependencies and description.

## Usage
```bash
R task equilibrium    # fuzzy matches build-equilibrium-snn
```

## Related
- `commands/tasks.md`
