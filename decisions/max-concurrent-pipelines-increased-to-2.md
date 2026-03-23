---
primitive: decision
date: 2026-03-23
status: active
decider: shael
upstream: [orchestration-fire-and-forget-dispatch, pipeline-kick-duplicate-dispatch-guard]
downstream: []
tags: [instance:main, pipeline, orchestration, concurrency, gate]
---

# max-concurrent-pipelines-increased-to-2

## Decision

Raise the pipeline concurrency limit from 1 to 2 in both `pipeline_autorun.py` (`MAX_CONCURRENT_PIPELINES = 2`) and `orchestration_engine.py` (`MAX_CONCURRENT = 2`).

## Rationale

With t1 (infrastructure) and t6 (lm-v2) both ready to run at the same time, the single-pipeline lock was a bottleneck. Infrastructure pipelines and research pipelines work on orthogonal parts of the codebase; there's no resource conflict. Two concurrent agents can make progress independently without stepping on each other.

## Implementation

- `pipeline_autorun.py`: `get_active_agent_pipeline()` now returns a list; gate checks `len(active) >= MAX_CONCURRENT_PIPELINES`.
- `orchestration_engine.py`: `kicked` changed from `bool` to `int` counter; all gate/revision/stall checks use `kicked < MAX_CONCURRENT`.
- Stall recovery and unclaimed dispatch recovery both respect the same limit.

## Alternatives Considered

- Keep limit at 1: simple, no coordination risk. Rejected: unnecessary serialization when pipelines are independent.
- Limit 3+: possible, but untested; may cause token/API pressure. Deferred.

## Consequences

Two pipelines can now run agents simultaneously. First validated with t1 + t6 on 2026-03-23. If agent collisions emerge, lower back to 1.
