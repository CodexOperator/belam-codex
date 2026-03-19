---
primitive: command
command: "belam autorun"
aliases: ["belam auto"]
description: "Auto-kick gated/stalled/revision pipelines (event-driven)"
category: pipeline
tags: [autorun, automation, gates, stall-detection, revisions]
---

# belam autorun

Event-driven automation. Check order: stale locks → gates → pending revisions → stalls. One pipeline at a time.

## Usage
```bash
belam autorun                       # Run all checks
belam autorun --check-locks         # Stale lock detection only
belam autorun --check-gates         # Gate checking only
belam autorun --check-revisions     # Pending revision requests only
belam autorun --check-stalled       # Stall detection only
belam autorun --dry-run             # Report only, don't kick
belam autorun --one <version>       # Kick a specific pipeline
```

## Revision Requests
Autorun picks up `pipeline_builds/{version}_revision_request.md` files. Create them via:
```bash
belam queue-revision <version> --context-file <path> --section "## Header" --priority high
```

## Related
- `commands/queue-revision.md`
- `skills/orchestration/SKILL.md`
- `lessons/checkpoint-and-resume-pattern.md`
