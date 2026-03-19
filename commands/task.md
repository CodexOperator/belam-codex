---
primitive: command
command: "belam task <name>"
aliases: []
description: "Show one task (fuzzy match)"
category: primitives
tags: [task, detail, fuzzy-match]
---

# belam task

Shows details for a single task, using fuzzy matching on the name. Use when you need the full context of a specific task including dependencies and description.

## Usage
```bash
belam task equilibrium    # fuzzy matches build-equilibrium-snn
```

## Related
- `commands/tasks.md`
