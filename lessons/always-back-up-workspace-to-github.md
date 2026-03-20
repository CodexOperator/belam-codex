---
primitive: lesson
date: 2026-03-20
source: session — Shael asked if workspace changes were backed up, they weren't
confidence: high
upstream: [decision/belam-codex-resurrection]
downstream: []
tags: [infrastructure, git, backup, redundancy]
---

# Always Back Up Workspace to GitHub

## Context

Over 8 days (March 12–20), the workspace accumulated 331 tracked files: a full CLI (belam, 545 lines + 883-line index engine), 40+ Python scripts, 95 primitives, complete memory hierarchy, pipeline orchestration infrastructure. The `machinelearning/` submodule was pushed to GitHub. The workspace itself had local commits but **no remote**.

## What Happened

Shael asked "has all these changes been backing up to GitHub?" The answer was no — only `machinelearning/` had a remote. The entire operational layer (the thing that makes everything else work) was one disk failure away from total loss. Additionally, the `belam` CLI script lived at `/home/ubuntu/.local/bin/belam` — outside the repo entirely, completely untracked.

## Lesson

**Every file that matters must be in a repo with a remote. If it's not pushed, it doesn't exist.**

Corollaries:
- Scripts and tools must live inside the tracked workspace, not in ad-hoc PATH locations
- "It's committed locally" is not a backup — it needs a remote
- Check for untracked critical files regularly (things installed to PATH, cron entries, system configs)

## Application

- **Heartbeat Task 6** must push both `belam-codex` and `machinelearning` repos
- When creating new scripts/tools, always put them in `scripts/` and symlink to PATH — never the reverse
- Periodically verify: `git remote -v` shows a remote, `git status` is clean, `git push` succeeds
- The `incarnate.sh` pattern (resurrection script in the repo) should be maintained as the repo evolves
