---
primitive: command
command: "R kickoff <ver>"
aliases: ["R kick"]
description: "Kick off a created pipeline (wake architect)"
category: pipeline
tags: [kickoff, pipeline, architect, launch]
---

# R kickoff

Kicks off a previously created pipeline by waking the architect agent. Use after `R pipeline launch` has created the pipeline structure.

## Usage
```bash
R kickoff <ver>
```

## Related
- `skills/launch-pipeline/SKILL.md`
- `decisions/agent-trio-architecture.md`
