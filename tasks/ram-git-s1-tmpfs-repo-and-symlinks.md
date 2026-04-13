---
primitive: task
status: open
priority: high
created: 2026-03-24
owner: belam
depends_on: [render-engine-simplification]
upstream: [ram-git-worktree-bootstrap]
downstream: [ram-git-s2-auto-commit-on-turn]
tags: [infrastructure, codex-engine, ram, git, builder-first]
project: codex-engine
pipeline_type: builder-first
pipeline_template: 
current_stage: 
pipeline_status: 
launch_mode: queued
---
# S1: Tmpfs Git Repo + Symlink Routing

## Builder Spec

Create a script `scripts/ram_git_bootstrap.sh` that:

1. **Creates tmpfs git repo:**
   - `mkdir -p /dev/shm/codex`
   - `cd /dev/shm/codex && git init`
   - Copy primitive namespace dirs from workspace into the RAM repo:
     `tasks/ decisions/ lessons/ memory/entries/ pipeline_builds/ pipelines/ goals/ knowledge/ projects/ workspaces/`
   - Initial commit: `git add -A && git commit -m "bootstrap from disk"`

2. **Symlinks workspace → RAM:**
   - For each dir above: `mv ~/.hermes/belam-codex/{dir} ~/.hermes/belam-codex/{dir}.disk-backup`
   - Then: `ln -s /dev/shm/codex/{dir} ~/.hermes/belam-codex/{dir}`
   - Dirs that stay on disk (NO symlink): `AGENTS.md SOUL.md IDENTITY.md USER.md MEMORY.md HEARTBEAT.md skills/ scripts/ commands/ modes/ templates/ docs/ machinelearning/`

3. **Teardown script** `scripts/ram_git_teardown.sh`:
   - Remove symlinks, restore `.disk-backup` dirs
   - Needed for clean shutdown and testing

4. **Verification:**
   - `ls -la ~/.hermes/belam-codex/tasks/` should show symlink → `/dev/shm/codex/tasks/`
   - `cat ~/.hermes/belam-codex/tasks/some-task.md` should work transparently
   - `echo "test" > ~/.hermes/belam-codex/tasks/test.md` should write to RAM
   - `ls /dev/shm/codex/tasks/test.md` should show the file

## Files to Create
- `scripts/ram_git_bootstrap.sh`
- `scripts/ram_git_teardown.sh`

## Files to Modify
- None (no existing code changes)

## Success Criteria
- [ ] Bootstrap script creates tmpfs repo with all primitive dirs
- [ ] Symlinks route transparently — existing scripts/agents see no difference
- [ ] Teardown script cleanly restores disk-direct access
- [ ] Total bootstrap time < 3 seconds
- [ ] Script is idempotent (safe to run twice)
