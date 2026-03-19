---
primitive: command
command: "belam revise <ver> --context \"...\""
aliases: ["belam rev"]
description: "Trigger Phase 1 revision cycle (coordinator-initiated)"
category: pipeline
tags: [revision, phase1, architect, critic, builder]
---

# belam revise

Triggers a coordinator-initiated Phase 1 revision cycle. Loops through architect→critic→builder→phase1_complete with the provided context guiding the revision focus.

## Usage
```bash
belam revise <ver> --context "description of what to revise"
```

## Related
- `decisions/agent-trio-architecture.md`
- `skills/pipelines/SKILL.md`
