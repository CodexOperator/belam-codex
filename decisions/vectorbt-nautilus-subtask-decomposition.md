---
primitive: decision
date: 2026-03-25
status: accepted
context: Breaking up the monolithic `setup-vectorbt-nautilus-pipeline` task into sequentially-pipelined subtasks
alternatives: [single monolithic pipeline, manual sequential execution, parallel execution]
rationale: The two-phase backtest stack (VectorBT PRO → NautilusTrader) has strong sequential dependencies — data ingestion must precede the strategy adapter, the adapter must precede validation and cost modeling. Decomposing into 6 subtasks allows each stage to be reviewed at a human gate before the next begins, and aligns with the builder-first template pattern for focused implementation work.
consequences: [6 pipeline runs will chain via heartbeat depends_on gate, s4/s5 can run in parallel once s3 completes, max_concurrent=1 enforces one at a time, human review at each phase1_complete gate]
project: snn-applied-finance
upstream: [decision/two-phase-backtest-workflow, decision/phase-n-generic-pipeline-template-architecture]
downstream: []
tags: [instance:main, backtesting, infrastructure, vectorbt, nautilus, subtasks]
promotion_status: exploratory
doctrine_richness: 2
contradicts: []
---

# VectorBT + NautilusTrader Subtask Decomposition

Break `setup-vectorbt-nautilus-pipeline` into 6 sequentially-chained subtasks:

```
s1 (env setup) → s2 (data pipeline) → s3 (strategy adapter) → s4 (walk-forward validation) → s6 (statistical validation)
                                                              └──→ s5 (transaction costs)
```

Each subtask runs through its own builder-first pipeline. Heartbeat Task 5 enforces ordering via `depends_on` — only launches the next task when the previous is `done`.
