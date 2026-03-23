---
primitive: command
name: R extract
usage: "R extract [instance]"
category: memory
alias: R ex
tags: [memory, extraction, session]
---

## R extract

Manually triggers memory extraction for the specified instance (default: `main`).

### What it does

1. Runs `scripts/extract_session_memory.sh --instance <instance>` to pull the current session transcript and prepare an extraction prompt in a temp file (`PROMPT_FILE`).
2. Spawns the **sage** agent via `openclaw agent --agent sage` with that prompt, using a timestamped session id (`mem-extract-<epoch>`).
3. Sage reads the prompt, distills what happened in the session, and writes entries into `memory/YYYY-MM-DD.md`.

### Usage

```bash
R extract          # extracts from main instance (default)
R extract staging  # extracts from a named instance
R ex               # alias
```

### When to use

- After a long work session to capture what happened before context resets
- During heartbeats to commit recent work to long-term memory
- Before handing off to another agent so context is preserved

### Notes

- If no session is found for the given instance, the script exits gracefully with a warning.
- The sage agent runs in an isolated session; it won't interfere with the current session.
- Extraction quality depends on how much session history is available.
