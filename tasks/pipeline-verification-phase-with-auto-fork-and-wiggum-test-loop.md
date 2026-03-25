---
primitive: task
status: complete
priority: high
created: 2026-03-24
owner: belam
depends_on: []
upstream: []
downstream: [codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing]
tags: [pipeline, testing, verification, wiggum, git-branch, infrastructure]
pipeline: pipeline-verification-phase-with-auto-fork-and-wiggum-test-loop
---

# Pipeline Verification Phase with Auto-Fork and Wiggum Test Loop

## Vision

Every pipeline automatically forks the codebase on launch, produces a test spec alongside the design, and runs a verification loop before merging back. No untested code reaches main.

## Current-Stack Implementation (Phase 1)

Uses existing tools — git branches on disk, wiggum skill, current orchestration. No RAM worktree dependency.

### Step 1: Auto-Fork on Pipeline Launch

In `pipeline_orchestrate.py` kickoff path:
```bash
git checkout -b pipeline/{name}
# all agent work happens on this branch
# merge to main on pipeline complete
```

- Branch created at pipeline_created stage
- All agent dispatches inherit the branch (cwd is same repo, branch is active)
- On pipeline archive/complete: `git checkout main && git merge pipeline/{name}`
- On pipeline discard: `git branch -D pipeline/{name}`

### Step 2: Architect Produces Test Spec

Architect prompt updated to produce TWO deliverables:
1. **Design doc** (existing) — architecture, implementation plan
2. **Test spec** — `pipeline_builds/{name}_test_spec.md`

Test spec format:
```markdown
# Test Specification: {pipeline name}

## Checklist
- [ ] T1: {description} — {pass criteria}
- [ ] T2: {description} — {pass criteria}
...

## Test Scripts
### T1: {description}
```bash
# command to run
# expected output / exit code
```

### Verification Method
- automated: run script, check exit code
- file-check: verify file exists / contains pattern
- manual: requires human inspection (flagged for coordinator)
```

### Step 3: Critic Reviews Test Coverage

Critic review expanded to include:
- Are all deliverables covered by at least one test?
- Are pass criteria unambiguous (machine-checkable)?
- Are there negative tests (what should NOT happen)?
- Flag any `manual` verification items for coordinator attention

### Step 4: Builder Verification Loop (Wiggum Pattern)

After builder completes implementation:
```
LOOP (wiggum steer at 70% timeout):
  1. Run test spec scripts
  2. Parse results against checklist
  3. Write results to pipeline_builds/{name}_test_results.md
  4. If all green → break, mark verification_complete
  5. If failures → fix code, re-run
  6. On steer timeout → write partial results + remaining failures
END LOOP
```

- Each loop iteration = git commit on branch (audit trail)
- Test results file updates on every iteration (coordinator sees diff)
- Max iterations configurable (default: 5) to prevent infinite loops

### Step 5: Merge or Escalate

- **All green:** auto-merge branch → main, pipeline continues to next phase
- **Partial failures after timeout:** coordinator gets test_results.md with remaining failures, decides: re-dispatch builder, escalate to architect for redesign, or accept with known issues
- **All red after max iterations:** block pipeline, alert coordinator

## Pipeline Lifecycle Integration

```
pipeline_created ──→ auto-fork branch
       ↓
architect_design ──→ design doc + test spec
       ↓
critic_design_review ──→ reviews both
       ↓
builder_implementation ──→ builds it
       ↓
builder_verification ──→ NEW: wiggum test loop
       ↓ (green)           ↓ (timeout/red)
verification_complete    escalate to coordinator
       ↓
merge branch → main
       ↓
[existing phases continue: experiment, analysis, etc.]
```

New stage: `builder_verification` inserted between `builder_implementation` and existing downstream stages.

## Changes Required

1. **pipeline_orchestrate.py** — git branch create on kickoff, merge on complete
2. **orchestration_engine.py** — add `builder_verification` stage to flow
3. **Agent prompts (architect)** — produce test spec alongside design
4. **Agent prompts (critic)** — review test coverage
5. **Agent prompts (builder)** — run verification loop after implementation
6. **Builder supervisor task** — wiggum loop with test runner logic
7. **pipeline_autorun.py** — handle verification_complete → next stage gate

## Future Enhancement (with D7 RAM Worktree)

- Branch lives in RAM git repo — faster, no disk I/O during test iterations
- Merge to main in RAM → sync daemon pushes to disk
- Agent branch isolation (D7.4) gives clean separation for concurrent pipelines
- Undo (D7.6) lets builder revert failed fix attempts instantly

## Success Criteria
- [ ] Pipeline launch auto-creates git branch
- [ ] Architect test spec produced for every pipeline
- [ ] Builder runs verification loop (wiggum pattern)
- [ ] Green tests auto-merge to main
- [ ] Failed tests escalate with clear report
- [ ] No changes to agent filesystem expectations (works on current stack)
