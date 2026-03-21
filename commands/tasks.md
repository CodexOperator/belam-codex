---
primitive: command
command: "belam tasks"
aliases: ["belam t"]
description: "List all tasks with status and priority"
category: primitives
tags: [tasks, list, status]
status: superseded
superseded_by: decision/codex-engine-v1-architecture
---

# belam tasks

Lists all task primitives with their status (open/blocked/in_pipeline/complete) and priority. Use to see what work is available or blocked.

## Usage
```bash
belam tasks
```

## Related
- `commands/task.md`
