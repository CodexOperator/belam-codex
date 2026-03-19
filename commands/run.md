---
primitive: command
command: "belam run <ver>"
aliases: ["belam r"]
description: "Run experiments locally for a pipeline. Auto-updates stages. Builder agent fixes errors."
category: experiment
tags: [experiment,run,analysis,local]
---

# belam run <ver>

Run experiments locally for a pipeline. Auto-updates stages. Builder agent fixes errors.

## Usage

```bash
belam run <ver>                    # Run experiments
belam run <ver> --analyze-local    # Run experiments → chain into analysis loop
belam run <ver> --dry-run          # Quick validation run
belam run <ver> --no-recovery      # Skip builder agent on errors
belam run <ver> --max-retries N    # Max builder recovery attempts (default: 2)
```

The `--analyze-local` flag chains directly into the orchestrated analysis pipeline
after experiments complete: data prep → architect → critic → builder → code review → LaTeX report.

## Related

- `commands/analyze-local.md` — standalone analysis (if experiments already ran)
- `commands/report.md` — standalone report build
