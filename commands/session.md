---
primitive: command
command: "belam -x session <subcommand>"
aliases: ["belam -x sess <subcommand>"]
description: "Session management: list, info, new (rotate), send, log (transcript tail)"
category: infrastructure
tags: [session, agents, transcript, rotate]
---

# belam -x session

Session management subcommands for inspecting and controlling agent sessions. Reads sessions.json directly without requiring openclaw CLI for list/info operations.

## Usage
```bash
belam -x session list [agent]           # List all sessions (or one agent)
belam -x session info <agent>           # Detailed session info (tokens, model, file)
belam -x session new <agent>            # Rotate to a fresh session (archives transcript)
belam -x session send <agent> "msg"     # Send a message to an agent
belam -x session send <agent> @file.md  # Send file contents as message
belam -x session log <agent>            # Show last 10 transcript messages
belam -x session log <agent> --tail 20  # Show last 20 messages
belam -x session log <agent> --verbose  # Include tool calls
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
