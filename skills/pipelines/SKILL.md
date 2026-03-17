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

## CLI Commands (`belam`)

The `belam` CLI (at `~/.local/bin/belam`, on PATH) wraps all pipeline and primitive scripts. **Prefer `belam` commands** — they work from any directory.

### Pipelines
```bash
belam pipelines                    # Dashboard: all pipelines with status
belam pipeline <ver>               # Detail view with full stage history
belam pipeline <ver> --watch [sec] # Live auto-refresh (default 10s)
belam pipeline update <ver> <cmd>  # Update stage (complete/start/block/status/show)
belam pipeline launch <ver> --desc "..."  # Create new pipeline
belam pipeline analyze <ver>       # Launch analysis pipeline
```

### Experiment Analysis
```bash
belam analyze <ver>                # Run analysis (auto-finds analysis pipeline)
belam analyze --detect             # Auto-detect new experiment results
belam analyze --check-gate <ver>   # Check Phase 3 gate
```

### Primitives
```bash
belam tasks                        # List tasks (with status + tags)
belam task <name>                  # Show one task (fuzzy match)
belam lessons                      # List lessons
belam projects                     # List projects
belam decisions                    # List decisions
```

### Memory & Status
```bash
belam status                       # Full overview: pipelines + tasks + memory + git
belam log "message"                # Quick memory entry
belam log -t tag "message"         # Tagged memory entry
belam consolidate                  # Run memory consolidation
```

### Shortcuts
`belam pl` = pipelines, `belam p` = pipeline, `belam t` = tasks, `belam l` = lessons,
`belam d` = decisions, `belam pj` = projects, `belam s` = status, `belam a` = analyze

## Direct Script Commands (equivalent)

Scripts are in the workspace `scripts/` directory. The `belam` CLI calls these under the hood.

| belam command | Script equivalent |
|---------------|-------------------|
| `belam pipelines` | `python3 scripts/pipeline_dashboard.py` |
| `belam pipeline <ver>` | `python3 scripts/pipeline_dashboard.py <ver>` |
| `belam pipeline update <ver> ...` | `python3 scripts/pipeline_update.py <ver> ...` |
| `belam pipeline launch <ver> ...` | `python3 scripts/launch_pipeline.py <ver> ...` |
| `belam pipeline analyze <ver>` | `python3 scripts/launch_analysis_pipeline.py <ver>` |
| `belam analyze <ver>` | `python3 scripts/analyze_experiment.py --notebook <ver>` |
| `belam analyze --check-gate <ver>` | `python3 scripts/analyze_experiment.py --check-gate <ver>` |
| `belam log "msg"` | `python3 scripts/log_memory.py "msg"` |

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

**Every agent MUST update the pipeline when starting or completing a stage.** This is not optional. Status is auto-bumped on completion — you no longer need to set status manually.

### When you START work:
```bash
belam pipeline update <version> start <stage> <your_agent_id>
```

### When you FINISH work:
```bash
belam pipeline update <version> complete <stage> "<what you did>" <your_agent_id>
```

The status auto-bumps based on the stage transition map. No manual `status` call needed.

### Examples:
```bash
belam pipeline update v4 start builder_implementation builder
belam pipeline update v4 complete builder_implementation "Notebook built, 32 experiments" builder
belam pipeline update v4 show
```

### Read before starting:
Read `pipelines/<version>.md` for current phase, stage history, feedback, and iteration log.
