---
primitive: task
title: Git-diff handoff context for pipeline stage transitions
status: open
priority: high
tags: [pipelines, orchestration, handoff, git, context]
pipeline: git-diff-handoff-context
upstream: []
downstream: []
created: 2026-03-25
---

# Git-Diff Handoff Context

## Problem

Pipeline handoffs currently give each agent a full-context dump (read these files, read the pipeline state, go). There's no summary of *what changed* since the last handoff. For forward-only builder-first pipelines this is tolerable, but for research pipelines with critic↔builder back-and-forth, agents waste context window re-reading unchanged files and have to infer what changed from review notes alone.

## Design

### Core mechanism: commit-hash snapshots at handoff boundaries

Each time a handoff fires (agent A completes → agent B dispatched), record the current git commit hash(es) in the pipeline state file:

```yaml
handoff_snapshots:
  - stage: architect_design
    agent: architect
    timestamp: 2026-03-25T15:00:00Z
    commits:
      workspace: abc1234
      machinelearning: def5678
  - stage: critic_review
    agent: critic
    timestamp: 2026-03-25T15:30:00Z
    commits:
      workspace: abc9999
      machinelearning: def9999
```

### Context assembly at dispatch time

When building the handoff message for the next agent:

1. Look up the **previous handoff snapshot** for the same agent (not just the last snapshot — the last time *this specific agent* touched this pipeline)
2. If found, run `git diff <old_hash>..HEAD -- <relevant_paths>` for both repos
3. Include the diff summary in the handoff message as a "Changes since your last session" block
4. If no previous snapshot exists (first touch), skip the diff section — full context only

### What gets diffed

Scope the diff to pipeline-relevant paths only (not the entire repo):
- **Workspace:** `pipeline_builds/<version>*`, `tasks/<version>.md`, `pipelines/<version>*.md`
- **Machinelearning:** `snn_applied_finance/research/pipeline_builds/<version>*`, `snn_applied_finance/notebooks/*<version>*`

### Diff format in handoff message

```
## Changes Since Your Last Session (critic_review → builder_implement)

### Workspace (3 files changed)
```diff
<truncated git diff --stat + key hunks>
```

### Research (1 file changed)  
```diff
<truncated git diff --stat + key hunks>
```
```

- Include `--stat` summary always
- Include full diff hunks if under 3000 chars, otherwise `--stat` only with a note to read the files
- For notebook files (.ipynb), use `--stat` only (diffs are noisy)

### Integration points

1. **`pipeline_orchestrate.py` → `build_handoff_message()`** — add diff section assembly
2. **`pipeline_update.py` or `orchestration_engine.py`** — record commit snapshot on each stage transition
3. **Pipeline state file** — add `handoff_snapshots` array

### Edge cases

- **First agent touch:** No prior snapshot → no diff, full context only (current behavior)
- **Same agent continues (checkpoint-and-resume):** Diff since the checkpoint commit
- **Git dirty (uncommitted changes):** Auto-commit before snapshotting, or use working tree diff
- **Repo not available:** Graceful fallback — skip diff section, log warning

## Deliverables

1. Helper function: `snapshot_handoff_commits(version, stage, agent)` — records commit hashes to pipeline state
2. Helper function: `build_handoff_diff(version, agent)` — generates diff text from last snapshot for this agent
3. Wire into `build_handoff_message()` — include diff section when available
4. Tests: verify snapshot recording, diff generation, truncation, graceful fallbacks

## Scope notes

- This is purely additive — existing full-context handoffs continue working, diff is an extra section
- No changes to template format or pipeline lifecycle
- Both repos (workspace + machinelearning) are already git-tracked, just need to capture HEAD at handoff time
