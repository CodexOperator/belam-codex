---
name: pipeline-dispatch
description: "Auto-dispatch next pipeline agent when current agent completes a stage"
metadata:
  openclaw:
    emoji: "🔄"
    events: ["agent:end"]
    requires:
      config: ["workspace.dir"]
---

# Pipeline Dispatch Hook

Fires on `agent:end`. Checks the pipeline state JSON for a pending dispatch
(written by `pipeline_orchestrate.py complete`). If found, spawns the next
agent via native OpenClaw `sessions_spawn` — no CLI subprocess needed.

This replaces `fire_and_forget_dispatch` (Popen → `openclaw agent`) with
a native hook that runs inside the agent runtime and has direct API access.
