# Builder-First Pipeline Template

## Flow

```
Phase 1: Builder (implement) → Builder (bugfix) → Critic (review) → [HUMAN GATE]
Phase 2: Architect (design) → Builder (implement) → Builder (bugfix) → Critic (review) → [HUMAN GATE]
Phase 3: Architect (design) → Builder (implement) → Builder (bugfix) → Critic (review) → [HUMAN GATE]
```

At each human gate (`p1_complete`, `p2_complete`), the pipeline pauses for Shael to review.
No auto-transition occurs. From these gates, the architect (or coordinator) can:
1. **Kick Phase 2** — `python3 scripts/pipeline_orchestrate.py <ver> kickoff --phase 2`
2. **Declare task done** — `python3 scripts/pipeline_orchestrate.py <ver> complete-task --agent architect --notes "reason"`
   - Archives the pipeline (status: archived)
   - Marks the parent task as done (status: done)
   - Notifies Telegram group

## When to Use
- Spec is already clear (decision exists, scope is tight)
- Implementation-heavy, design-light work
- Infrastructure tasks with well-defined success criteria

## Stage Definitions

### Phase 1 — Builder-First Implementation

#### `p1_builder_implement`
- Receives: task spec + success criteria + any reference files
- Produces: working code, committed to repo
- Handoff: test results + file manifest → next builder

#### `p1_builder_bugfix`
- Receives: previous builder's code + test results
- Produces: bug fixes, edge cases, test coverage improvements
- Handoff: updated test results + fix summary → critic

#### `p1_critic_review`
- Receives: full implementation + test results + task spec
- Produces: review document (pass/fail, issues found, suggestions)
- Handoff: review doc → human gate

### Phase 2 — Architect-Led Refinement

#### `p2_architect_design`
- Receives: critic review + implementation state
- Produces: Phase 2 spec with specific changes/improvements
- Handoff: P2 spec → builder_implement (next phase)

#### `p2_builder_implement`
- Builder implements Phase 2 design changes

#### `p2_builder_bugfix`
- Fix bugs and edge cases from Phase 2 implementation

#### `p2_critic_review`
- Final review of Phase 2 implementation

## Subtask Convention
Break the parent task into sequential subtasks named:
```
{parent-slug}-s1-{description}
{parent-slug}-s2-{description}
{parent-slug}-s3-{description}
```

Each subtask runs through the full pipeline independently. Later subtasks can depend on earlier ones.

## Stage Transitions
<!-- machine-readable: parsed by template_parser.py -->
<!-- Phase-based format: phases define stage sequences, gates, and block routing -->
```yaml
first_agent: builder
type: builder-first

phases:
  1:
    stages:
      - { role: builder, action: implement, session: fresh }
      - { role: builder, action: bugfix, session: continue }
      - { role: critic, action: review, session: fresh }
    gate: human

  2:
    stages:
      - { role: architect, action: design, session: fresh }
      - { role: builder, action: implement, session: fresh }
      - { role: builder, action: bugfix, session: continue }
      - { role: critic, action: review, session: fresh }
    gate: human

  3:
    stages:
      - { role: architect, action: design, session: fresh }
      - { role: builder, action: implement, session: fresh }
      - { role: builder, action: bugfix, session: continue }
      - { role: critic, action: review, session: fresh }
    gate: human

block_routing:
  critic:
    review: builder

complete_task_agent: architect
```

## Human Gates

Both `p1_complete` and `p2_complete` are **human gates** — the pipeline stops and waits for manual action. No auto-dispatch occurs.

### Actions at a Human Gate

| Action | Command | Effect |
|--------|---------|--------|
| Kick Phase 2 | `pipeline_orchestrate.py <ver> kickoff --phase 2` | Starts Phase 2 flow |
| Complete task | `pipeline_orchestrate.py <ver> complete-task --agent architect --notes "reason"` | Archives pipeline + marks task done |
| Manual transition | `pipeline_orchestrate.py <ver> complete <gate_stage> --agent <role> --notes "..."` | Advance to specific next stage |

### Architect "Task is Done" Path

When the architect (at `p1_complete` or `p2_complete`) determines the task is fully satisfied:

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
