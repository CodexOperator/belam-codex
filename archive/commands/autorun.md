---
primitive: command
command: "R autorun"
aliases: ["R auto"]
description: "Auto-kick gated/stalled/revision pipelines (event-driven)"
category: pipeline
tags: [autorun, automation, gates, stall-detection, revisions]
---

# R autorun

Event-driven automation. Check order: stale locks → gates → pending revisions → stalls. One pipeline at a time.

## Usage
```bash
R autorun                       # Run all checks
R autorun --check-locks         # Stale lock detection only
R autorun --check-gates         # Gate checking only
R autorun --check-revisions     # Pending revision requests only
R autorun --check-stalled       # Stall detection only
R autorun --dry-run             # Report only, don't kick
R autorun --one <version>       # Kick a specific pipeline
```

## Revision Requests
Autorun picks up `pipeline_builds/{version}_revision_request.md` files. Create them via:
```bash
R queue-revision <version> --context-file <path> --section "## Header" --priority high
```

## Related
- `commands/queue-revision.md`
- `skills/orchestration/SKILL.md`
- `lessons/checkpoint-and-resume-pattern.md`
