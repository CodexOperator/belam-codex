# Builder-First Pipeline Template

## Flow

```
Phase 1: Builder (implement) → Builder (bugfix) → Critic (review) → Architect (Phase 2 draft)
Phase 2: Builder (implement P2) → Builder (bugfix) → Critic (review) → [done or Architect drafts P3]
```

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

## Pipeline File Fields
```yaml
type: builder-first
stages: [builder_implement, builder_bugfix, critic_review, architect_phase2]
current_stage: builder_implement
```
