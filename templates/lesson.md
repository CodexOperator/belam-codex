---
primitive: lesson
fields:
  date:
    type: date
    required: true
  source:
    type: string
  confidence:
    type: string
    enum: [high, medium, low]
    default: medium
  project:
    type: string
  tags:
    type: string[]
  applies_to:
    type: string[]
cli:
  list: "belam lessons"
  show: "belam lesson <name>"
  shortcut: "belam l"
---
