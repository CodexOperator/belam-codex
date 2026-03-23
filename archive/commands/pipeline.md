---
primitive: command
command: "R pipeline <ver>"
aliases: ["R p <ver>"]
description: "Detail view of a pipeline with stage history, plus update/launch/analyze subcommands"
category: pipeline
tags: [pipeline, detail, stages, watch]
status: superseded
superseded_by: decision/codex-engine-v1-architecture
---

# R pipeline

Shows detailed view of a specific pipeline version including stage history, current phase, and agent activity. Supports `--watch` for live auto-refresh, plus subcommands for managing pipeline lifecycle.

## Usage
```bash
R pipeline <ver>              # Detail view
R pipeline <ver> --watch      # Live auto-refresh
R pipeline update <ver> ...   # Update pipeline stage
R pipeline launch <ver> ...   # Create new pipeline
R pipeline analyze <ver>      # Launch analysis pipeline
```

## Related
- `skills/pipelines/SKILL.md`
- `decisions/orchestration-architecture.md`
