---
primitive: command
command: "R report <ver>"
aliases: []
description: Build LaTeX→PDF report from approved analysis (orchestrated via pipeline_orchestrate.py)
category: analysis
tags: [report, latex, pdf, analysis]
---

# R report

Converts experiment analysis markdown into a professional LaTeX report and compiles to PDF. Output lives alongside experiment results.

## Usage
```bash
R report <version>                # Orchestrated: builds LaTeX→PDF via report-build action
```

## Pipeline Integration

When triggered by the orchestrator (after `local_analysis_code_review` passes):
1. Tries auto-build via pandoc + pdflatex
2. Falls back to spawning builder agent with reasoning for custom LaTeX
3. Output: `notebooks/local_results/{version}/{version}_report.pdf`

## Related
- `commands/analyze-local.md`
- `commands/run.md`
