---
primitive: runbook
fields:
  status:
    type: string
    required: true
    default: active
    enum: [draft, active, deprecated]
  category:
    type: string
    enum: [pipeline, infrastructure, deployment, maintenance, onboarding]
  tags:
    type: string[]
  last_executed:
    type: date
  execution_count:
    type: number
    default: 0
  automation_script:
    type: string
    description: "Path to script that automates this runbook (if exists)"
  estimated_time:
    type: string
---
