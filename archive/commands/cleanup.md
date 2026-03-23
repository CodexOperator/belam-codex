---
primitive: command
command: "R cleanup"
aliases: ["R clean"]
description: "Kill stale agent sessions (default: dry run)"
category: infrastructure
tags: [cleanup, sessions, maintenance]
---

# R cleanup

Finds and kills stale agent sessions. Runs in dry-run mode by default so you can review before actually terminating anything.

## Usage
```bash
R cleanup          # dry run — show what would be killed
R cleanup --force  # actually kill stale sessions
```

## Related
- `decisions/agent-session-isolation.md`
