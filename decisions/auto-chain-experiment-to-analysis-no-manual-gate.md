---
primitive: decision
date: 2026-03-23
status: active
importance: 3
upstream: [phase2-human-gate, analysis-phase2-gate-mandatory]
downstream: []
tags: [instance:main, pipeline, gate, experiment, analysis]
promotion_status: exploratory
doctrine_richness: 10
contradicts: []
---

# auto-chain-experiment-to-analysis-no-manual-gate

## Decision

The pipeline gate between experiment completion and local analysis is **fully automatic** — no human gate between them. The phase2 human gate fires only after local analysis is complete.

## Flow

```
experiment_complete
  → [auto] analysis gate opens
  → local_analysis_architect / critic / builder / code_review / report_build
  → local_analysis_complete
  → [HUMAN GATE] phase2 direction file required
  → phase2 pipeline kicks
```

## Rationale

- Local analysis is deterministic and doesn't require human judgment to initiate
- Blocking analysis on human input wastes time (experiment results sit idle)
- Shael requested this gate change on 2026-03-23 to remove the manual step between experiment and analysis
- The phase2 human gate (direction file) is the meaningful decision point, not the analysis kickoff

## Implementation

- `pipeline_autorun.py` sweep detects `experiment_complete` status → calls `orchestrate_local_analysis()`
- `check_running_experiments()` transitions dead-PID completions to `experiment_complete`
- `pipeline_update.py` writes state to both flat and subdirectory paths so sweep sees correct status
