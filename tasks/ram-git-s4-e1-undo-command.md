---
primitive: task
status: open
priority: medium
created: 2026-03-24
owner: belam
depends_on: [ram-git-s3-f-label-git-diff-output]
upstream: [ram-git-undo-primitive]
downstream: []
tags: [infrastructure, codex-engine, ram, git, undo, builder-first]
project: codex-engine
pipeline_type: builder-first
---

# S4: e1 undo Command

## Builder Spec

Add `e1 undo` to the codex engine as a first-class coordinate action that reverts changes using the RAM git tree.

1. **In `scripts/codex_engine.py`**, add undo handling to the e1 mode:
   - `e1 undo` → `cd /dev/shm/codex && git reset --hard HEAD~1` (last turn)
   - `e1 undo N` → `git reset --hard HEAD~N` (N turns back)
   - `e1 undo F{n}` → read `/dev/shm/codex/.f_labels`, find commit for F{n}, run `git revert <commit> --no-edit`
   - Return: the git diff of what was undone (so the agent sees what changed back)

2. **Validation:**
   - If N > total commits, return error with max available
   - If F{n} doesn't exist in `.f_labels`, return error with available F labels
   - If RAM repo doesn't exist, return error suggesting bootstrap

3. **Output format:**
   - Show the reverse diff (what was undone) in F-label format
   - Example: `Undone F3 (tasks/some-task.md):\n@@ ...\n-status: done\n+status: open`

## Files to Modify
- `scripts/codex_engine.py` — add undo subcommand to e1 mode

## Reference Files
- `scripts/ram_git_diff.sh` (from S3 — F label mapping format)
- `scripts/ram_git_commit.sh` (from S2 — commit structure)

## Success Criteria
- [ ] `e1 undo` reverts last turn in < 10ms
- [ ] `e1 undo N` reverts N turns correctly
- [ ] `e1 undo F{n}` reverts specific F-label change
- [ ] Clear error messages for invalid inputs
- [ ] Returns reverse diff showing what was undone
