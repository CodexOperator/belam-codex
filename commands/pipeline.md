---
primitive: command
command: "belam pipeline <ver>"
aliases: ["belam p <ver>"]
description: "Detail view of a pipeline with stage history, plus update/launch/analyze subcommands"
category: pipeline
tags: [pipeline, detail, stages, watch]
status: superseded
superseded_by: decision/codex-engine-v1-architecture
---

# belam pipeline

Shows detailed view of a specific pipeline version including stage history, current phase, and agent activity. Supports `--watch` for live auto-refresh, plus subcommands for managing pipeline lifecycle.

## Usage
```bash
belam pipeline <ver>              # Detail view
belam pipeline <ver> --watch      # Live auto-refresh
belam pipeline update <ver> ...   # Update pipeline stage
belam pipeline launch <ver> ...   # Create new pipeline
belam pipeline analyze <ver>      # Launch analysis pipeline
```

## Related
- `skills/pipelines/SKILL.md`
- `decisions/orchestration-architecture.md`
