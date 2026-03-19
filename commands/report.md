---
primitive: command
command: "belam report <ver>"
aliases: []
description: "Build LaTeX report from experiment analysis and export as PDF"
category: analysis
tags: [report, latex, pdf, analysis]
---

# belam report

Converts experiment analysis markdown into a professional LaTeX report and compiles to PDF. Output lives alongside experiment results.

## Usage
```bash
belam report <version>                # Auto: pandoc MD→PDF
belam report <version> --agent        # Use builder agent to write custom LaTeX
belam report <version> --compile-only # Just run pdflatex on existing .tex
```

## Pipeline Integration

When triggered by the orchestrator (after `local_analysis_code_review` passes):
1. Tries auto-build via pandoc + pdflatex
2. Falls back to spawning builder agent with reasoning for custom LaTeX
3. Output: `notebooks/local_results/{version}/{version}_report.pdf`

## Related
- `commands/analyze-local.md`
- `commands/run.md`
