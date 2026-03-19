---
primitive: command
command: "belam analyze-local <ver>"
aliases: ["belam al <ver>"]
description: "Analyze local experiment results — generates comprehensive MD + plots"
category: analysis
tags: [analysis, experiment, local, plots]
---

# belam analyze-local

Analyzes local experiment results from the pipeline's `local_results/{version}/` directory. Generates:
- Comprehensive analysis markdown document with statistical tables
- Deep analysis plots (accuracy by type, accuracy vs sharpe scatter, fold stability, scale analysis, training dynamics, significance heatmap)
- Summary in `pipeline_builds/` for reference

## Usage
```bash
belam analyze-local <version>                # Full analysis + plots
belam analyze-local <version> --skip-plots   # MD only, reuse existing plots
belam analyze-local <version> --no-extra-plots  # Skip deep analysis plots
belam analyze-local <version> --report       # Also build LaTeX→PDF report
```

## Related
- `commands/report.md`
- `commands/run.md`
- `commands/analyze.md`
