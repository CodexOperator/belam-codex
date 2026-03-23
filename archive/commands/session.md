---
primitive: command
command: "R -x session <subcommand>"
aliases: ["R -x sess <subcommand>"]
description: "Session management: list, info, new (rotate), send, log (transcript tail)"
category: infrastructure
tags: [session, agents, transcript, rotate]
---

# R -x session

Session management subcommands for inspecting and controlling agent sessions. Reads sessions.json directly without requiring openclaw CLI for list/info operations.

## Usage
```bash
R -x session list [agent]           # List all sessions (or one agent)
R -x session info <agent>           # Detailed session info (tokens, model, file)
R -x session new <agent>            # Rotate to a fresh session (archives transcript)
R -x session send <agent> "msg"     # Send a message to an agent
R -x session send <agent> @file.md  # Send file contents as message
R -x session log <agent>            # Show last 10 transcript messages
R -x session log <agent> --tail 20  # Show last 20 messages
R -x session log <agent> --verbose  # Include tool calls
```

## Subcommands

| Subcommand | Description |
|------------|-------------|
| `list`     | List sessions for all agents or a specific one |
| `info`     | Show session ID, model, token count, file size, age |
| `new`      | Archive current transcript and clear sessions.json entry |
| `send`     | Dispatch a message via `openclaw agent` CLI |
| `log`      | Tail recent messages from the JSONL transcript |

## Related
- `commands/spawn.md`
