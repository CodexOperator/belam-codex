---
name: pipelines
description: >
  List, create, check, and archive Implementation Pipelines — the 3-phase research lifecycle
  (autonomous build → human-in-the-loop → iterative research) for SNN notebook versions.
  Use when: user says "pipelines", "pipeline list", "launch pipeline", "archive pipeline",
  "pipeline status", or asks about active/completed notebook versions.
  Also use when an agent needs to check pipeline state, verify phase gates, or find its
  current build stage.
---

# Pipelines

Implementation Pipelines track notebook versions through 3 phases:
1. **Phase 1:** Autonomous build (architect → critic → builder)
2. **Phase 2:** Human-in-the-loop (feedback → revision → rebuild)
3. **Phase 3:** Iterative research (gated on phase 2 completion, scored proposals)

All phases live in a **single notebook** as top-level sections.

## Commands

All scripts are in the workspace `scripts/` directory.

### List active pipelines
```bash
python3 scripts/launch_pipeline.py --list
```

### Create a new pipeline
```bash
python3 scripts/launch_pipeline.py <version> --desc "<description>" [--priority critical|high|medium|low] [--tags snn,finance,...]
```

### Check phase 3 gate
```bash
python3 scripts/analyze_experiment.py --check-gate <version>
```

### Check if archivable
```bash
python3 scripts/launch_pipeline.py <version> --check-archive
```

### Archive a completed pipeline
```bash
python3 scripts/launch_pipeline.py <version> --archive
```

### Generate phase 3 proposal (autonomous)
```bash
python3 scripts/analyze_experiment.py --propose-auto '{"version":"<ver>","id":"<id>","hypothesis":"...","justification":"...","score":<1-10>,"proposed_by":"<role>"}'
```
Score ≥ 7 = auto-approved, 4-6 = flagged for review, < 4 = rejected.

## Pipeline files

- **Template:** `templates/pipeline.md`
- **Instances:** `pipelines/<version>.md` (one per notebook version)
- **Build artifacts:** `SNN_research/machinelearning/snn_applied_finance/research/pipeline_builds/<version>_*`
- **State JSON:** `pipeline_builds/<version>_state.json`

## For agents — MANDATORY

**Every agent MUST update the pipeline when starting or completing a stage.** This is not optional.

### When you START work:
```bash
python3 scripts/pipeline_update.py <version> start <stage> <your_agent_id>
```

### When you FINISH work:
```bash
python3 scripts/pipeline_update.py <version> complete <stage> "<what you did>" <your_agent_id>
python3 scripts/pipeline_update.py <version> status <new_overall_status>
```

### Examples:
```bash
python3 scripts/pipeline_update.py v4 start builder_implementation builder
python3 scripts/pipeline_update.py v4 complete builder_implementation "Notebook built, 32 experiments, all cells tested" builder
python3 scripts/pipeline_update.py v4 status phase1_code_review
```

### View current state:
```bash
python3 scripts/pipeline_update.py <version> show
```

### Read before starting:
Read `pipelines/<version>.md` for current phase, stage history, feedback, and iteration log.
