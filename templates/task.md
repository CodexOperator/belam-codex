---
primitive: task
fields:
  status:
    type: string
    required: true
    default: open
    enum: [open, in-progress, blocked, done]
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
cli:
  list: "belam tasks"
  show: "belam task <name>"
  shortcut: "belam t"
---
