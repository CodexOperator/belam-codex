---
primitive: memory_log
fields:
  timestamp:
    type: datetime
    required: true
    description: "ISO 8601 timestamp, auto-generated at creation"
  category:
    type: string
    required: true
    enum: [insight, decision, preference, context, event, technical, relationship]
    description: "Type of memory — auto-detected if not specified"
  importance:
    type: integer
    required: true
    default: 3
    minimum: 1
    maximum: 5
    description: "1=trivial, 3=noteworthy, 5=critical"
  tags:
    type: string[]
    description: "Cross-referencing tags, comma-separated on CLI"
  source:
    type: string
    description: "What triggered this memory (session, experiment, conversation, etc.)"
  content:
    type: string
    required: true
    description: "The actual memory content"
  status:
    type: string
    enum: [active, consolidated, archived, superseded]
    default: active
    description: "Lifecycle state — entries are immutable, only status changes"
cli:
  log: "R log 'message'"
  log_tagged: "R log -t tag 'message'"
  consolidate: "R consolidate"
  consolidate_all: "R consolidate --all-agents"
---

# Memory Log Entry Template

## Example Usage

```yaml
---
primitive: memory_log
timestamp: "2026-03-17T03:00:00Z"
category: technical
importance: 4
tags: [snn, v4, gradients]
source: experiment
content: "Spike-count readout causes dead neurons — always use membrane potential readout"
status: active
---
```

## Category Guide

| Category     | When to Use                                                    |
|--------------|----------------------------------------------------------------|
| insight      | Ah-ha moments, pattern recognition, conceptual breakthroughs  |
| decision     | Choices made, directions set, trade-offs resolved             |
| preference   | User preferences, style choices, communication patterns       |
| context      | Environmental context, setup details, current state           |
| event        | Significant happenings, milestones, state transitions         |
| technical    | Code findings, architecture patterns, debugging conclusions   |
| relationship | People interactions, collaboration patterns, trust signals    |

## Importance Guide

| Level | Meaning                                              |
|-------|------------------------------------------------------|
| 1     | Trivial — minor detail, probably won't need again    |
| 2     | Low — marginally useful, nice to have                |
| 3     | Noteworthy — worth keeping, may be referenced later  |
| 4     | High — important finding, likely to inform decisions |
| 5     | Critical — must not be forgotten, changes direction  |
