---
primitive: command
command: "R analyze-local <ver>"
aliases: ["R al <ver>"]
description: Orchestrated local analysis — data prep + architect→critic→builder loop with reasoning
category: analysis
tags: [analysis,local,orchestration,experiment]
---

# R analyze-local

Orchestrated local analysis pipeline. Routes through the same orchestrator as `R run`:

1. **Data prep** — runs `analyze_local_results.py` to generate statistical tables + plots
2. **Architect** — writes comprehensive analysis report (reasoning enabled)
3. **Critic review** — validates analysis quality and statistical rigor
4. **Builder** — implements additional analysis scripts the architect specified
5. **Code review** — critic validates the builder's code
6. **Report build** — auto-builds LaTeX→PDF from approved analysis

Uses the existing `pipeline_orchestrate.py` with `local-analysis` action.
All agents get reasoning/extended thinking enabled for deep analysis work.

## Usage
```bash
R analyze-local <version>            # Full orchestrated analysis pipeline
R analyze-local <version> --dry-run  # Preview without kicking agents
```

## Orchestrator Actions
```bash
# Direct orchestrator access (same thing):
R orchestrate <ver> local-analysis
R orchestrate <ver> report-build
```

## Related
- `commands/report.md` — LaTeX report build stage
- `commands/run.md` — experiment execution (precedes analysis)
- `commands/analyze.md` — Colab experiment analysis (different from local)
