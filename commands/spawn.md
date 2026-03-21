---
primitive: command
command: "belam -x spawn <agent> \"<task>\""
aliases: ["belam -x sp <agent> \"<task>\""]
description: "Spawn a fresh agent session: auto-rotates then dispatches task"
category: infrastructure
tags: [spawn, agents, session, dispatch]
---

# belam -x spawn

Spawn a fresh agent session. Automatically rotates (archives) the agent's current session first, then dispatches the given task via `openclaw agent`. Supports reading the task from a file via `@path` syntax.

## Usage
```bash
belam -x spawn <agent> "task description"
belam -x spawn <agent> @/path/to/prompt.md
belam -x spawn <agent> "task" --bg          # background (no wait)
belam -x spawn <agent> "task" --timeout 300 # custom timeout (seconds)
belam -x sp <agent> "task"                  # alias
```

## Options

| Option | Description |
|--------|-------------|
| `--bg` | Dispatch in background without waiting for completion |
| `--timeout <sec>` | Max seconds to wait (default: 600) |
| `--model <alias>` | Model alias: sonnet, opus, haiku |

## What It Does
1. Verifies the agent exists in openclaw.json
2. Rotates the agent's current session (`session new`)
3. Dispatches the task via `openclaw agent --agent <name> -m <task>`

## Related
- `commands/session.md`
