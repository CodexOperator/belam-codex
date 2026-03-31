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
  promotion_status:
    type: string
    default: exploratory
    enum: [exploratory, candidate, promoted, validated]
  doctrine_richness:
    type: integer
    default: 0
    range: [0, 10]
  contradicts:
    type: string[]
    default: []
cli:
  list: "R decisions"
  show: "R decision <name>"
  shortcut: "R d"
---
