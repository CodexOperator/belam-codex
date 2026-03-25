# Critic Review: git-diff-handoff-context — p1_critic_review

**Reviewer:** Critic 🔍
**Date:** 2026-03-25
**Verdict:** ✅ APPROVED — 0 BLOCKs, 0 HIGH FLAGs, 1 MED FLAG, 1 LOW FLAG

## Summary

Clean, well-scoped infrastructure addition. `handoff_diff.py` (232L) records git HEAD snapshots at stage boundaries and generates scoped diffs for returning agents. Orchestrator integration is correct — snapshot at step 0.5 (before `pipeline_update.py` save at step 1), diff in handoff message build (after step 1). 17/17 tests GREEN (verified independently).

## What Was Reviewed

1. **`scripts/handoff_diff.py`** (232L) — core implementation
2. **`tests/test_handoff_diff.py`** (17 tests) — unit + integration tests
3. **`scripts/pipeline_orchestrate.py`** — integration points (3 locations: `build_handoff_message` L131-134, `orchestrate_complete` L719-722, `orchestrate_block` L951-954)
4. **`pipeline_builds/git-diff-handoff-context_state.json`** — live state file with 3 snapshots

## Verifications Performed

| # | Check | Result |
|---|-------|--------|
| V1 | 17/17 pytest GREEN (independent run) | ✅ |
| V2 | Snapshot records workspace + ML HEAD hashes | ✅ |
| V3 | Missing repo returns graceful `_note` instead of error | ✅ |
| V4 | Agent-specific lookup walks backwards correctly (builder→s3, critic→s2) | ✅ |
| V5 | First-touch returns empty string (no prior snapshot) | ✅ |
| V6 | Same-commit returns empty (no changes) | ✅ |
| V7 | Diff truncation at 3000 chars falls to stat-only | ✅ |
| V8 | ipynb filter excludes notebook diffs | ✅ |
| V9 | `handoff_snapshots` key preserved through `pipeline_update.py` load/save cycles | ✅ |
| V10 | Orchestrator ordering: snapshot (step 0.5) → pipeline_update (step 1) → handoff message (step 2+) | ✅ |
| V11 | Both complete and block flows have try/except fallback for snapshot | ✅ |
| V12 | `subprocess.run` uses list form (no shell=True) — no injection risk | ✅ |
| V13 | Timeouts: 5s for rev-parse, 15s for diff | ✅ |
| V14 | CLI entry point works: `handoff_diff.py show/diff/snapshot` | ✅ |
| V15 | Glob pathspecs in `_relevant_paths` work with git diff (list-form avoids shell expansion) | ✅ |

## FLAGs

### FLAG-1 MED: `_has_ipynb` checks substring in entire diff text, not filenames

```python
def _has_ipynb(diff_text: str) -> bool:
    return '.ipynb' in diff_text
```

This checks for `.ipynb` anywhere in the full diff output — including hunks, comments, and string literals. If a `.py` file diff contains the string `.ipynb` (e.g., `path = 'notebooks/foo.ipynb'`), the notebook filter triggers and suppresses full hunks for that entire repo.

**Impact:** False positive falls back to stat-only view (less informative but not incorrect). The scenario is plausible — handoff_diff.py itself contains `.ipynb` in its docstring, so diffs to this file would trigger it.

**Fix:** Check against the `--stat` output (filenames only) instead of the full diff text. Or pass `--stat` output to `_has_ipynb` and check the full diff separately.

### FLAG-2 LOW: Shared scripts in every pipeline's workspace scope

`_relevant_paths` includes `scripts/handoff_diff.py`, `scripts/pipeline_orchestrate.py`, and `scripts/orchestration_engine.py` for ALL pipelines. Changes to these shared files appear in every pipeline's diff. Arguable tradeoff — agents should know about infra changes, but it adds noise when only pipeline-specific changes matter.

## Architecture Assessment

**PASS** — The design is clean and well-suited:

- **Snapshot-then-diff pattern:** Record HEAD at completion, generate diff at next dispatch. Correct separation of concerns.
- **Agent-scoped snapshots:** Each agent sees changes since THEIR last session, not the previous agent's. Correct for the multi-agent handoff model.
- **Graceful degradation:** Missing repos, first touch, no changes — all handled without errors. Try/except in orchestrator means failures are non-fatal.
- **State co-location:** `handoff_snapshots` stored in the pipeline state JSON alongside stage data. No new files, no new coordination mechanism.
- **Scoped diffs:** Only pipeline-relevant paths shown, not the whole repo. Reduces noise significantly.

## Test Coverage Assessment

**Good.** 17 tests covering: snapshot recording (3), agent lookup (3), diff output formatting (4), path scoping (2), git HEAD (3), integration (1), graceful fallbacks (1). The integration test does a real snapshot→diff cycle with mocked state. `TestGetGitHead` tests against the actual workspace repo.

**Gap:** No test exercises the `_has_ipynb` path with a false positive (diff text containing '.ipynb' in a non-notebook context). Minor — matches FLAG-1.

## Bugfix Stage Assessment

Builder reported "no bugs found" — consistent with my review. The implementation is straightforward (git rev-parse + git diff, JSON state management, string formatting) with no complex logic that would harbor subtle bugs.
