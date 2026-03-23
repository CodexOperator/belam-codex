---
primitive: command
command: "R log \"msg\""
aliases: []
description: "Quick memory entry, optionally tagged"
category: memory
tags: [memory, log, quick-entry]
lm_include: true
---

# R log

Appends a quick entry to today's memory file. Use for capturing thoughts, progress notes, or observations without opening the file manually. Supports tagging for categorization.

## Usage
```bash
R log "completed phase 1 review"
R log -t pipeline "v0.8.1 kicked off"
```

## Related
- `commands/consolidate.md`
- `decisions/hierarchical-memory-system.md`
