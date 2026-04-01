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
cli:
  list: "R tasks"
  show: "R task <name>"
  shortcut: "R t"
---
