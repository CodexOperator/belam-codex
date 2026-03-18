---
primitive: launch-pipeline
name: Pipeline Launcher
description: >
  Manages the creation and kickoff of new pipelines from eligible tasks.
  Covers gate checking, pipeline creation, orchestrator-driven architect wakeup,
  and task status bookkeeping. Used by heartbeat (Sonnet) for autonomous launches
  and by coordinator (Opus) for manual launches.
fields:
  scripts:
    type: object
    description: "Scripts involved in the launch flow"
    properties:
      launch_pipeline:
        type: string
        default: "scripts/launch_pipeline.py"
        description: "Creates pipeline markdown + state JSON from template. --kickoff flag triggers orchestrator."
      launch_analysis_pipeline:
        type: string
        default: "scripts/launch_analysis_pipeline.py"
        description: "Creates analysis pipeline. --kickoff flag triggers orchestrator."
      pipeline_orchestrate:
        type: string
        default: "scripts/pipeline_orchestrate.py"
        description: "Completes pipeline_created stage, wakes architect via openclaw agent CLI, writes handoff record."
      pipeline_update:
        type: string
        default: "scripts/pipeline_update.py"
        description: "State tracker called by orchestrator. Updates markdown + state JSON + Telegram group."
  cli:
    type: object
    description: "belam CLI commands"
    properties:
      kickoff:
        type: string
        default: "belam kickoff <version>"
        description: "Kick off an already-created pipeline (wake architect via orchestrator)"
      create_and_kickoff:
        type: string
        default: "belam pipeline launch <version> --desc '...' --priority <p> --tags <t> --project <proj> --kickoff"
        description: "Create pipeline AND kick off in one step"
      create_analysis:
        type: string
        default: "belam pipeline analyze <version> --desc '...' --kickoff"
        description: "Create and kick off analysis pipeline"
      handoffs:
        type: string
        default: "belam handoffs"
        description: "Check for stuck/pending handoffs"
      verify:
        type: string
        default: "belam orchestrate <version> verify"
        description: "Retry failed handoffs for a specific pipeline"
  gates:
    type: object
    description: "Gate rules that must pass before launching"
    properties:
      analysis_phase2:
        type: string
        description: "New notebook versions require analysis phase 2 complete on previous version"
      task_status:
        type: string
        default: "open"
        description: "Task must be status: open (not in_pipeline, blocked, or done)"
      dependencies:
        type: string
        description: "All depends_on entries must be satisfied"
  transition:
    type: object
    description: "The transition that kickoff triggers"
    properties:
      from_stage:
        type: string
        default: "pipeline_created"
      to_stage:
        type: string
        default: "architect_design"
      target_agent:
        type: string
        default: "architect"
      wake_method:
        type: string
        default: "openclaw agent --agent architect"
        description: "Fresh session via openclaw agent CLI (not sessions_send to existing session)"
  skill:
    type: string
    default: "skills/launch-pipeline/SKILL.md"
    description: "Corresponding skill with full decision flow for agents"
---

# Pipeline Launcher

## What It Does

Bridges the gap between **eligible tasks** and **running pipelines**. The launcher:
1. Checks gates (analysis phase 2, task dependencies)
2. Creates pipeline files (markdown + state JSON) from templates
3. Kicks off via orchestrator (`pipeline_created` → `architect_design`)
4. Wakes architect with fresh session and rich handoff context
5. Updates task status to `in_pipeline`

## Flow

```
Task (status: open, deps met)
  │
  ├─ Pipeline exists but never kicked off?
  │    → belam kickoff <version>
  │
  └─ No pipeline yet?
       → belam pipeline launch <version> --desc "..." --kickoff
            │
            ├─ Creates pipelines/<version>.md from template
            ├─ Creates pipeline_builds/<version>_state.json
            └─ Calls pipeline_orchestrate.py complete pipeline_created
                  │
                  ├─ pipeline_update.py: state + markdown + Telegram
                  ├─ openclaw agent --agent architect: fresh session wake
                  ├─ Handoff record → pipelines/handoffs/
                  └─ If wake fails: retry once, then alert group
```

## Heartbeat Integration

Sonnet reads `HEARTBEAT.md` Task 1 each cycle, which references `templates/heartbeat.md` for the decision framework. When eligible tasks are found:

```bash
# Already-created, never kicked off
belam kickoff <version>

# New pipeline from task
belam pipeline launch <version> --desc "..." --priority <p> --tags <t> --project <proj> --kickoff

# Space multiple kickoffs
sleep 5  # between calls
```

After launch, update task file: `status: open` → `status: in_pipeline`, add `pipeline: <version>`.

## Related Primitives

- `templates/pipeline.md` — builder pipeline instance template
- `templates/analysis_pipeline.md` — analysis pipeline instance template
- `templates/orchestrator.md` — stage execution orchestrator
- `templates/heartbeat.md` — heartbeat decision framework (references this launcher)
- `skills/launch-pipeline/SKILL.md` — agent-facing skill with full decision flow
