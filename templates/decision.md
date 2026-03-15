---
primitive: decision
fields:
  status:
    type: string
    required: true
    default: proposed
    enum: [proposed, accepted, rejected, superseded]
  date:
    type: date
    required: true
  context:
    type: string
  alternatives:
    type: string[]
  rationale:
    type: string
  consequences:
    type: string[]
  project:
    type: string
  tags:
    type: string[]
---
