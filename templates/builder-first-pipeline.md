# Builder-First Pipeline Template

## Flow

```
Phase 1: Builder (implement) → Builder (bugfix) → Critic (review) → [HUMAN GATE] → Architect review
Phase 2: Builder (implement P2) → Builder (bugfix) → Critic (review) → [HUMAN GATE] → Architect review
```

At each human gate (`phase1_complete`, `phase2_complete`), the pipeline pauses for Shael to review.
No auto-transition occurs. From these gates, the architect (or coordinator) can:
1. **Kick Phase 2** — `python3 scripts/pipeline_orchestrate.py <ver> kickoff --phase2`
2. **Declare task done** — `python3 scripts/pipeline_orchestrate.py <ver> complete-task --agent architect --notes "reason"`
   - Archives the pipeline (status: archived)
   - Marks the parent task as done (status: done)
   - Notifies Telegram group

## When to Use
- Spec is already clear (decision exists, scope is tight)
- Implementation-heavy, design-light work
- Infrastructure tasks with well-defined success criteria

## Stage Definitions

### `builder_implement`
- Receives: task spec + success criteria + any reference files
- Produces: working code, committed to repo
- Handoff: test results + file manifest → next builder

### `builder_bugfix`
- Receives: previous builder's code + test results
- Produces: bug fixes, edge cases, test coverage improvements
- Handoff: updated test results + fix summary → critic

### `critic_review`
- Receives: full implementation + test results + task spec
- Produces: review document (pass/fail, issues found, suggestions)
- Handoff: review doc → architect (if issues) or → done (if clean pass)

### `architect_phase2`
- Receives: critic review + implementation state
- Produces: Phase 2 spec with specific changes/improvements
- Handoff: P2 spec → builder_implement (next phase)

## Subtask Convention
Break the parent task into sequential subtasks named:
```
{parent-slug}-s1-{description}
{parent-slug}-s2-{description}
{parent-slug}-s3-{description}
```

Each subtask runs through the full pipeline independently. Later subtasks can depend on earlier ones.

## Stage Transitions
<!-- machine-readable: parsed by orchestration_engine.py -->
<!-- gate: human → stops auto-dispatch, waits for manual kick -->
```yaml
first_agent: builder
pipeline_fields:
  type: builder-first
  stages: [builder_implement, builder_bugfix, critic_review, architect_phase2]

transitions:
  # Phase 1 — builder-first
  # session: fresh = reset agent session (cross-agent or after gate)
  # session: continue = keep same session (same-agent sequential stages)
  pipeline_created:        [builder_implement,    builder, "Task spec ready. Implement per task file and success criteria.", session: fresh]
  builder_implement:       [builder_bugfix,       builder, "Implementation done. Review code, fix bugs, add edge case coverage.", session: continue]
  builder_bugfix:          [critic_review,        critic,  "Code complete + bugfixed. Review implementation against task spec.", session: fresh]
  critic_review:           [phase1_complete,      system,  "Phase 1 review passed. Ready for human review or Phase 2.", gate: human, session: fresh]
  # Phase 1 blocks — critic sends back to builder
  builder_apply_blocks:    [critic_review,        critic,  "Blocks fixed. Re-review implementation.", session: fresh]

  # Phase 2 — same flow with architect drafting direction first
  phase2_architect_design:        [phase2_builder_implement,    builder, "Phase 2 direction ready. Implement changes per phase2 spec.", session: fresh]
  phase2_builder_implement:       [phase2_builder_bugfix,       builder, "Phase 2 implementation done. Fix bugs and edge cases.", session: continue]
  phase2_builder_bugfix:          [phase2_critic_review,        critic,  "Phase 2 code complete. Review against phase2 spec.", session: fresh]
  phase2_critic_review:           [phase2_complete,             system,  "Phase 2 review passed. Pipeline complete.", gate: human, session: fresh]
  phase2_builder_apply_blocks:    [phase2_critic_review,        critic,  "Phase 2 blocks fixed. Re-review.", session: fresh]

status_bumps:
  builder_implement:               phase1_build
  builder_bugfix:                  phase1_build
  critic_review:                   phase1_code_review
  phase1_complete:                 phase1_complete
  phase2_builder_implement:        phase2_build
  phase2_builder_bugfix:           phase2_build
  phase2_critic_review:            phase2_code_review
  phase2_complete:                 phase2_complete

start_status_bumps:
  builder_implement:               phase1_build
  phase2_builder_implement:        phase2_build

# Human gates: these stages have NO outgoing transition — pipeline pauses
human_gates:
  - phase1_complete    # Shael reviews before Phase 2 or task completion
  - phase2_complete    # Shael reviews before Phase 3 or task completion
```

## Human Gates

Both `phase1_complete` and `phase2_complete` are **human gates** — the pipeline stops and waits for manual action. No auto-dispatch occurs.

### Actions at a Human Gate

| Action | Command | Effect |
|--------|---------|--------|
| Kick Phase 2 | `pipeline_orchestrate.py <ver> kickoff --phase2` | Starts Phase 2 flow |
| Complete task | `pipeline_orchestrate.py <ver> complete-task --agent architect --notes "reason"` | Archives pipeline + marks task done |
| Manual transition | `pipeline_orchestrate.py <ver> complete <gate_stage> --agent <role> --notes "..."` | Advance to specific next stage |

### Architect "Task is Done" Path

When the architect (at `phase1_complete` or `phase2_complete`) determines the task is fully satisfied:

```bash
python3 scripts/pipeline_orchestrate.py <version> complete-task \
  --agent architect \
  --notes "Implementation satisfies all requirements. No Phase 2 needed."
```

This command:
1. Sets pipeline status to `archived` with archive date and reason
2. Finds the parent task (from pipeline's `task:` frontmatter field) and sets status to `done`
3. Writes agent memory for continuity
4. Sends a Telegram notification to the pipeline group chat
