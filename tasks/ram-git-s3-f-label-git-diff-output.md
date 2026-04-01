---
primitive: task
status: open
priority: high
created: 2026-03-24
owner: belam
depends_on: [ram-git-s2-auto-commit-on-turn]
upstream: [scrap-r-labels-keep-f-labels-as-raw-git-diff]
downstream: [ram-git-s4-e1-undo-command]
tags: [infrastructure, codex-engine, ram, git, f-labels, builder-first]
project: codex-engine
pipeline_type: builder-first
pipeline_template: 
current_stage: 
pipeline_status: 
launch_mode: queued
---
# S3: F Labels as Raw Git Diff Output

## Builder Spec

Replace the render engine's R/F label formatting pipeline with raw `git diff` output. F labels become numbered git diffs — nothing more.

1. **Diff generation script** `scripts/ram_git_diff.sh`:
   - `cd /dev/shm/codex`
   - `git diff HEAD~1` (or `git diff <from>..<to>` for multi-turn)
   - Output format: raw git diff (same as GitHub renders — `+`/`-` lines, file headers)
   - Number each file change as `F1`, `F2`, `F3`... in sequence
   - Example output:
     ```
     F1: tasks/ram-git-s1-tmpfs-repo-and-symlinks.md
     @@ -3,7 +3,7 @@
     -status: open
     +status: done
     
     F2: decisions/some-decision.md
     +++ new file
     @@ -0,0 +1,15 @@
     +---
     +primitive: decision
     ...
     ```

2. **Cockpit plugin integration:**
   - Replace current diff injection (R/F label formatted output) with a call to `ram_git_diff.sh`
   - Inject the raw output into the system prompt / turn context
   - If no changes since last turn, inject nothing (empty diff = no F labels)
   - **Remove:** DiffEntry processing, R-label generation, content formatting, HeartbeatTrigger wake-on-diff-count

3. **F label → commit mapping:**
   - Each F label maps to a file within a commit. Store a simple mapping file:
   - `/dev/shm/codex/.f_labels` — JSON: `{"F1": {"commit": "abc123", "file": "tasks/foo.md"}, ...}`
   - Updated by `ram_git_diff.sh` on each run
   - This mapping is what `e1 undo F{n}` will consume (S4)

## Files to Create
- `scripts/ram_git_diff.sh`

## Files to Modify
- `scripts/codex_render.py` — remove: DiffEntry content storage, R/F label formatting, HeartbeatTrigger class, inotify diff accumulation. Keep: supermap rendering, coordinate resolution, status endpoint.
- Cockpit plugin (`codex-cockpit/index.ts` or equivalent) — replace diff injection source

## Reference Files
- `decisions/scrap-r-labels-keep-f-labels-as-raw-git-diff.md` — the governing decision
- `scripts/codex_render.py` — current render engine (identify what to remove)
- `scripts/ram_git_commit.sh` (from S2 — commit structure)

## Success Criteria
- [ ] F labels are raw `git diff` output with numbered file headers
- [ ] Zero processing between git and agent — pipe through only
- [ ] `.f_labels` mapping file updated on each diff
- [ ] R labels no longer produced anywhere
- [ ] HeartbeatTrigger and inotify diff chain removed from render engine
- [ ] Existing supermap rendering unaffected
