---
primitive: command
command: "belam cleanup"
aliases: ["belam clean"]
description: "Kill stale agent sessions (default: dry run)"
category: infrastructure
tags: [cleanup, sessions, maintenance]
---

# belam cleanup

Finds and kills stale agent sessions. Runs in dry-run mode by default so you can review before actually terminating anything.

## Usage
```bash
belam cleanup          # dry run — show what would be killed
belam cleanup --force  # actually kill stale sessions
```

## Related
- `decisions/agent-session-isolation.md`
