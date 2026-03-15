---
primitive: project
fields:
  status:
    type: string
    required: true
    default: active
    enum: [planning, active, paused, complete, archived]
  priority:
    type: string
    enum: [critical, high, medium, low]
  owner:
    type: string
  tags:
    type: string[]
  start_date:
    type: date
  target_date:
    type: date
  repo:
    type: string
  location:
    type: string
---
