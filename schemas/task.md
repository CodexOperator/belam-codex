---
primitive: task
fields:
  status:
    type: string
    required: true
    default: open
    enum: [open, active, in_pipeline, in-progress, blocked, queued, done]
  priority:
    type: string
    enum: [critical, high, medium, low]
    default: medium
  owner:
    type: string
  due:
    type: date
  tags:
    type: string[]
  estimate:
    type: string
  parent:
    type: string
  depends_on:
    type: string[]
  project:
    type: string
  pipeline_template:
    type: string
    default: ""
    description: "Template slug (e.g. builder-first, research). References pt namespace."
  current_stage:
    type: string
    default: ""
    description: "Current pipeline stage. Normally derived, writable for override."
  pipeline_status:
    type: string
    default: ""
    enum: ["", queued, launching, in_pipeline, stalled, complete]
    description: "Pipeline lifecycle status mirror."
  launch_mode:
    type: string
    default: queued
    enum: [queued, active]
    description: "queued respects MAX_CONCURRENT; active bypasses it."
  pipeline_template_path:
    type: string
    default: ""
    description: "Absolute/relative path to the template markdown. Overrides pipeline_template slug when set."
  pipeline_runtime:
    type: object
    default: {}
    description: |
      Runtime overrides for CLI-agnostic dispatch. Resolution precedence:
      task > pipeline template defaults > CLI registry defaults.
      Deep-merge policy: scalars override, arrays replace, maps deep-merge.
      Recognized sub-fields:
        schema_version  — integer (current: 1)
        defaults        — map applied to every stage
        cli_aliases     — map of symbolic alias -> registered CLI key
        phase_overrides — map keyed by phase id (e.g. "p1")
        stage_overrides — map keyed by canonical stage name
        Within any of the above blocks:
          cli              — CLI key or alias from state/cli_registry.yaml
          args             — list appended to the CLI's default_args
          launcher         — popen | tmux (slice 1: popen only)
          cockpit_mode     — shared | per-role
          context          — list of symbolic tools/personas
          ask_on_question  — main_session | telegram | both
cli:
  list: "R tasks"
  show: "R task <name>"
  shortcut: "R t"
---
