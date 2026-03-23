---
primitive: command
command: "R orchestrate"
aliases: ["R orch"]
description: "Direct orchestrator access (complete/block/start/status/verify/revise)"
category: pipeline
tags: [orchestration, direct-access, stages]
lm_include: true
---

# R orchestrate

Direct access to the pipeline orchestrator for manual stage management. Supports completing, blocking, starting, checking status, verifying, and revising pipeline stages.

## Usage
```bash
R orchestrate complete <ver> <stage>
R orchestrate block <ver> <stage> --reason "..."
R orchestrate start <ver> <stage>
R orchestrate status <ver>
R orchestrate verify <ver>
R orchestrate revise <ver> --context "..."
```

## Related
- `skills/orchestration/SKILL.md`
- `decisions/orchestration-architecture.md`
