---
primitive: agent
fields:
  agent_id:
    type: string
    required: true
    description: "OpenClaw agent ID (matches openclaw.json)"
  status:
    type: string
    default: active
    enum: [active, inactive, deprecated]
  role:
    type: string
    required: true
  model:
    type: string
  workspace:
    type: string
  telegram_bot:
    type: string
  group_chat:
    type: string
  skills:
    type: string[]
  knowledge_files:
    type: string[]
  communicates_with:
    type: string[]
    description: "Other agent IDs this agent interacts with"
  tags:
    type: string[]
---
