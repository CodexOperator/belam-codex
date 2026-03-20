---
name: memory-extract
description: "Auto-extract memories/lessons/decisions from the just-ended session on bootstrap"
metadata:
  openclaw:
    emoji: "🧠"
    events: ["agent:bootstrap"]
    requires:
      config: ["workspace.dir"]
---

# Memory Extract Hook

On every `agent:bootstrap` event (triggered by `/new` or `/reset`), this hook:

1. Finds the most recent completed session JSONL for this instance
2. Parses it into a readable transcript (deterministic bash — zero tokens)
3. Spawns a fire-and-forget subagent to extract primitives (memories/lessons/decisions)
4. Creates a tracking primitive so the render engine shows extraction progress

The subagent:
- Creates primitives via `log_memory.py` and `create_primitive.py`
- Tags every primitive with `instance:<name>` and optionally `persona:<name>`
- Wires upstream/downstream edges where relationships are obvious
- Commits and pushes any new files
- Updates the tracker to `complete` when done

This replaces manual memory consolidation and the export_agent_conversations pipeline
for the main instance. Sub-agent sessions are handled via the orchestrator integration
in `pipeline_orchestrate.py`.
