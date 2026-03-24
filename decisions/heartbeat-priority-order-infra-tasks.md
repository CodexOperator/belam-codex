---
primitive: decision
importance: 3
tags: [instance:main, heartbeat, orchestration, prioritization, infrastructure]
related: [heartbeat-md-e0-primary-path, remove-e0-sweep-from-heartbeat]
created: 2026-03-24
---

# Heartbeat: Priority-Ordered Infra Task Launch

## Decision

Heartbeat's infrastructure pipeline queue now explicitly selects the next task in priority order (high → medium → low) while respecting both `depends_on` and `upstream` dependency chains before launching.

## Rationale

Previously heartbeat just picked "next eligible" without priority sorting. This caused low-priority tasks (like container-build-and-test) to be launched when higher-priority engine work was sitting open. After the containerization incident, Shael confirmed: Docker work holds until critical engine tasks clear.

## Rules

1. Sort open infra tasks: high priority first, then medium, then low
2. For each candidate: verify all `depends_on` tasks are `done`
3. Also check `upstream` edges for implicit dependencies
4. Launch the first task that passes both checks
5. MAX_CONCURRENT=1 for infra pipelines — never launch if one is active

## Updated in HEARTBEAT.md

The Task 5 section of HEARTBEAT.md now documents this ordering explicitly.
