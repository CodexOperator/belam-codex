---
primitive: command
command: "belam orchestrate"
aliases: ["belam orch"]
description: "Direct orchestrator access (complete/block/start/status/verify/revise)"
category: pipeline
tags: [orchestration, direct-access, stages]
---

# belam orchestrate

Direct access to the pipeline orchestrator for manual stage management. Supports completing, blocking, starting, checking status, verifying, and revising pipeline stages.

## Usage
```bash
belam orchestrate complete <ver> <stage>
belam orchestrate block <ver> <stage> --reason "..."
belam orchestrate start <ver> <stage>
belam orchestrate status <ver>
belam orchestrate verify <ver>
belam orchestrate revise <ver> --context "..."
```

## Related
- `skills/orchestration/SKILL.md`
- `decisions/orchestration-architecture.md`
