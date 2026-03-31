---
primitive: decision
status: active
created: 2026-03-21
owner: belam
upstream: [decision/orchestration-architecture, task/persistent-extend-and-indexed-subops]
downstream: []
tags: [orchestration, dependencies, automation, cascading]
promotion_status: exploratory
doctrine_richness: 10
contradicts: []
---

# Automated Dependency Resolution on Completion

## Decision

When a pipeline archives or a task completes, the orchestration engine automatically scans all tasks whose `depends_on` references the completed slug and marks that dependency as satisfied. If all dependencies are now met, the task becomes eligible for pipeline launch.

## Rationale

Currently dependency satisfaction is checked passively (heartbeat reads `depends_on`, checks if referenced tasks are complete). But dependency *updates* are manual — a human or the coordinator has to notice that an upstream completed and update the downstream. This caused a stale `depends_on: [build-orchestration-engine-v1]` on t8 when orch V1 had already archived.

## Implementation

### Trigger Points
1. **Pipeline archive** (`e0 9` or `launch_pipeline.py --archive`): scan tasks referencing this pipeline's slug
2. **Task completion** (status → complete/archived): scan tasks referencing this task's slug
3. **Sweep gate check** (existing): already checks dependencies, but only reads — doesn't write

### Cascade Logic
```python
def resolve_downstream_deps(completed_slug: str):
    for task_file in tasks_dir.glob('*.md'):
        fm = parse_frontmatter(task_file)
        deps = fm.get('depends_on', [])
        if completed_slug in deps:
            # Check if ALL deps are now satisfied
            all_met = all(_is_complete(d) for d in deps)
            if all_met:
                # Emit gate-open event
                print(f"  GATE OPEN: {task_file.stem} — all dependencies met")
                # Don't auto-change status — just log eligibility
                # Heartbeat Task 1.2 handles pipeline spawn decision
```

### What It Does NOT Do
- Does not auto-launch pipelines (that's heartbeat Task 1.2's job)
- Does not auto-change task status (task owner decides)
- Only logs eligibility as a gate-open event

### Integration Points
- `handle_complete()` in orchestration_engine.py: call after stage completion
- `e0 9` (archive): call as step 6 of archive post-actions
- Sweep: already handles this passively, but active cascade is faster

## Design Conversation
Shael + Belam, 2026-03-21 19:37 UTC. Shael noted dependency updates should be automated — prompted by a stale dep on t8 that wasn't cleared when orch V1 archived.
