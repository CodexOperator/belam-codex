---
primitive: command
command: "belam handoffs"
aliases: []
description: "Check for stuck pipeline handoffs awaiting agent pickup"
category: pipeline
tags: [handoffs, pipeline, stuck, orchestration]
---

# belam handoffs

Checks for pipeline handoffs that are stuck or awaiting agent pickup. Scans the orchestration system for pending handoff files that haven't been consumed within the expected window.

## Usage
```bash
belam handoffs
```

## What It Checks
- Handoff files in the pipeline orchestration directory
- Stages flagged as awaiting handoff but not yet picked up
- Stalled agent-to-agent transitions

## Related
- `commands/autorun.md`
- `commands/kickoff.md`
- `skills/orchestration/SKILL.md`
