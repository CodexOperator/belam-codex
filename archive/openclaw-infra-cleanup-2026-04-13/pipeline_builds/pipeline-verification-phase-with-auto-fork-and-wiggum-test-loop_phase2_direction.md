# Phase 2 Direction: Pipeline Verification — Git Branching + Lesson Injection

## Context
Phase 1 shipped the verification loop (D4+D5+D7): `pipeline_verify.py` test runner, wiggum steer integration, `builder_verification` stage in the pipeline flow. Critic approved, all 8 tests pass.

Phase 2 adds the two deferred features: auto-fork git branches and lesson injection into agent context.

## D1: Auto-Fork Git Branch per Pipeline (Deferred from Phase 1)

**Critic FLAG-1 from Phase 1:** Concurrent branch race — `fire_and_forget_dispatch` is async, stash+checkout has no lock.

**Phase 2 approach: worktree-based, not checkout-based.**

Use `git worktree add` instead of `git checkout -b`:
```bash
git worktree add /tmp/pipeline-{version} -b pipeline/{version}
```

This avoids ALL concurrent branch conflicts because:
- Each pipeline gets its own working directory in /tmp
- Main workspace stays on `main` branch — never touched
- Multiple pipelines can run simultaneously with zero contention
- Agent dispatch just needs `cwd=/tmp/pipeline-{version}` passed to Popen

**Implementation in `pipeline_orchestrate.py`:**

1. On pipeline kickoff (`pipeline_created` → `architect_design`):
   - `git worktree add /tmp/pipeline-{version} -b pipeline/{version}`
   - Store worktree path in `_state.json`: `"worktree": "/tmp/pipeline-{version}"`

2. All agent dispatches for this pipeline:
   - Pass `cwd=state['worktree']` to Popen in `fire_and_forget_dispatch()`
   - Agent reads/writes to the worktree — isolated from other pipelines

3. On `verification_complete` (all tests pass):
   - `cd /workspace && git merge pipeline/{version}` (merge worktree branch → main)
   - `git worktree remove /tmp/pipeline-{version}`
   - Clean up branch: `git branch -d pipeline/{version}`

4. On pipeline discard/archive:
   - `git worktree remove /tmp/pipeline-{version}` + `git branch -D pipeline/{version}`

**Key: no locks, no stash, no checkout conflicts.** Each pipeline is physically isolated.

## D8: Lesson Injection into Agent Dispatch

**Already implemented in `orchestration_engine.py` `_files_for_stage()` during this session.** The code:
- Reads pipeline/task tags from frontmatter
- Matches against lesson tags (stripping `instance:` prefixes)
- Scores by overlap count
- Injects top 10 most relevant lessons into `files_to_read`

**Phase 2 work:** Verify it works end-to-end. Specifically:
1. Confirm agents actually READ the injected lesson files (check agent prompts)
2. Add a test to the test spec: "T9: Lesson injection — dispatch includes relevant lessons in files_to_read"
3. Consider adding a `--lessons` flag to `pipeline_orchestrate.py` to show which lessons would be injected for a given pipeline

## D9: Verification Loop Auto-Retry

Phase 1 has a single verification pass. Phase 2 adds:
- If `pipeline_verify.py` returns failures, builder gets re-dispatched with the failure report
- Max 3 iterations (configurable via `VERIFICATION_MAX_RETRIES` in state JSON)
- Each iteration appends to `_test_results.md` (audit trail)
- On max retries exhausted: escalate to coordinator with full failure history

The wiggum steer timer already handles per-iteration timeouts. The loop logic goes in `dispatch_verification()`:
```
for i in range(max_retries):
    dispatch builder with test failures
    if all pass: break
    else: include failure report in next dispatch
```

## Priority
D1 (worktree) > D9 (auto-retry) > D8 (verify lesson injection)

## Success Criteria
- [ ] `git worktree` creates isolated branch per pipeline on launch
- [ ] Concurrent pipelines don't interfere (test: launch 2 simultaneously)
- [ ] Merge to main on verification_complete
- [ ] Builder re-dispatched on test failures (up to 3x)
- [ ] Lesson injection verified in agent dispatch
