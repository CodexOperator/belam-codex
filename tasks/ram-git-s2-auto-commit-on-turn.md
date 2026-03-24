---
primitive: task
status: open
priority: high
created: 2026-03-24
owner: belam
depends_on: [ram-git-s1-tmpfs-repo-and-symlinks]
upstream: [ram-git-diff-pipeline]
downstream: [ram-git-s3-f-label-git-diff-output]
tags: [infrastructure, codex-engine, ram, git, builder-first]
project: codex-engine
pipeline_type: builder-first
---

# S2: Auto-Commit on Turn Boundary

## Builder Spec

Create a mechanism that commits all RAM repo changes at turn boundaries so that every turn = one git commit.

1. **Script** `scripts/ram_git_commit.sh`:
   - `cd /dev/shm/codex`
   - `git add -A`
   - Check if there are staged changes: `git diff --cached --quiet || git commit -m "turn $(date -u +%Y%m%dT%H%M%SZ)"`
   - Exit 0 whether or not a commit was made (idempotent)
   - Should complete in < 50ms

2. **Cockpit plugin hook point:**
   - In `codex-cockpit/index.ts` (or equivalent plugin entry), add a post-turn hook that shells out to `ram_git_commit.sh`
   - This runs after every agent turn completes, before the next message is processed
   - If the cockpit plugin doesn't have a post-turn hook mechanism, document what's needed and create a standalone watcher as fallback:
     - `scripts/ram_git_autocommit.sh` — inotify on `/dev/shm/codex` with 2s debounce, commits on quiet period

3. **Commit message format:**
   - `turn YYYYMMDDTHHMMSSZ` for auto-commits
   - Include changed file list in commit body: `git diff --cached --name-only`

## Files to Create
- `scripts/ram_git_commit.sh`
- Possibly `scripts/ram_git_autocommit.sh` (fallback watcher)

## Files to Modify
- Cockpit plugin if hook point exists (document location for builder)

## Reference Files
- `scripts/ram_git_bootstrap.sh` (from S1 — shows repo location)
- Cockpit plugin: `~/.npm-global/lib/node_modules/openclaw/` (read-only, find hook points)

## Success Criteria
- [ ] Every agent turn produces exactly one commit (or zero if no changes)
- [ ] Commit completes in < 50ms
- [ ] `git log --oneline` in `/dev/shm/codex` shows clean turn-by-turn history
- [ ] No commits on turns with no file changes
