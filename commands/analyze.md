---
primitive: command
command: "belam analyze <ver>"
aliases: ["belam a <ver>"]
description: "Run experiment analysis (auto-finds pipeline)"
category: analysis
tags: [analysis, experiment, phase2]
lm_include: true
---

# belam analyze

Runs experiment analysis for a notebook version, automatically finding the associated pipeline. Use after Phase 1 completes to evaluate results before proceeding to Phase 2.

## Usage
```bash
belam analyze <ver>
```

## Related
- `lessons/analysis-phase2-gate-mandatory.md`
- `commands/pipeline.md`
