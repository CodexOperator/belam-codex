---
name: memory-extract
description: "Save session context and extract memories on /new or /reset"
metadata:
  openclaw:
    emoji: "🧠"
    events: ["command"]
    requires:
      config: ["workspace.dir"]
---

# Memory Extract Hook

Combined session-memory + extraction hook. Fires on `/new` and `/reset` commands.

**Step 1 — Save session context** (replaces bundled session-memory):
- Writes a summary markdown file to `memory/YYYY-MM-DD-HHMM.md`
- Uses timestamp slug (no LLM call — keeps it fast)

**Step 2 — Extract primitives** (fire-and-forget):
- Runs `extract_session_memory.sh` to parse the ended session transcript
- Spawns sage agent in background to create memory/lesson/decision primitives
- Tags every primitive with `instance:<name>`

All errors logged to `logs/memory-extract.log` for debugging.
