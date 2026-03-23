---
primitive: command
command: "R run <ver>"
aliases: ["R r"]
description: "Run experiments locally for a pipeline. Auto-updates stages. Builder agent fixes errors."
category: experiment
tags: [experiment,run,analysis,local]
---

# R run <ver>

Run experiments locally for a pipeline. Auto-updates stages. Builder agent fixes errors.

## Usage

```bash
R run <ver>                    # Run experiments
R run <ver> --analyze-local    # Run experiments → chain into analysis loop
R run <ver> --dry-run          # Quick validation run
R run <ver> --no-recovery      # Skip builder agent on errors
R run <ver> --max-retries N    # Max builder recovery attempts (default: 2)
```

The `--analyze-local` flag chains directly into the orchestrated analysis pipeline
after experiments complete: data prep → architect → critic → builder → code review → LaTeX report.

## Related

- `commands/analyze-local.md` — standalone analysis (if experiments already ran)
- `commands/report.md` — standalone report build
