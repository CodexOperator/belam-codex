---
primitive: command
command: "R build <ver>"
aliases: []
description: "Build a notebook version"
category: pipeline
tags: [build, notebook, execution]
lm_include: true
---

# R build

Builds a specific notebook version. Use when a pipeline's builder stage needs to execute or when manually triggering a notebook build.

## Usage
```bash
R build <ver>
```

## Related
- `commands/pipeline.md`
- `commands/kickoff.md`
