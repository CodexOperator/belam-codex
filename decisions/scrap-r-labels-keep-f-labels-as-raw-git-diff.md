---
primitive: decision
slug: scrap-r-labels-keep-f-labels-as-raw-git-diff
title: Scrap R Labels, Keep F Labels as Raw Git Diff
importance: 5
tags: [instance:main, render-engine, diff, codex-engine, architecture, simplification]
created: 2026-03-24
---

# Decision: Scrap R Labels, Keep F Labels as Raw Git Diff

## Context
The R/F label diff system (render engine → inotify → label formatting → cockpit injection) has been unreliable — stale state, weird rendering, and token-heavy. The coordinator already tracks changes from context and can reprint any supermap section on demand. The system adds complexity without proportional value.

## Decision

### Kill
- **R labels** — rendered summary diff lines. No longer produced.
- **Pin/rewind emoji tracking** — the 📌🔄 system for marking/rewinding diff anchors.
- **Render engine diff processing pipeline** — inotify → DiffEntry → R/F label formatting → cockpit injection chain.

### Keep
- **Coordinate actions** (e0/e1/e2/e3) — the navigation and edit grammar stays and will be refined.
- **Supermap** — injected at boot via cockpit plugin, always current from disk.
- **F labels** — redefined as **raw git diff output**. Literally `git diff` piped through with `+`/`-` lines (GitHub-style rendering). No processing, no formatting, just pipe.
- **RAM git worktree** with symlinks (tasks: ram-git-worktree-bootstrap, ram-git-diff-pipeline, ram-git-sync-daemon).

### New: `e1 undo F{n}`
- Pick any F label from diff history → git revert/reset that change in the filesystem.
- One subcommand in the e1 edit suite. Wraps `git revert` or `git reset` on the RAM git tree.
- Trivial to implement because every edit in the RAM worktree is already a commit.

## Rationale
- **Fewer tokens**: a git diff of a changed primitive is 5-15 lines vs full supermap re-render or formatted R labels.
- **Zero processing**: no intermediate render pipeline. `git diff` is the source of truth, piped directly.
- **No stale state**: the "supermap being weird" problems disappear — no intermediate diff state to corrupt.
- **Git is already the source of truth**: cutting out the middleman.
- **Vanilla workflow**: the coordinator already tracks changes turn-to-turn and reprints sections for verification. This just formalizes what's already working.

## What Changes in the Render Engine
- `codex_render.py` loses: DiffEntry content storage, R/F label formatting, HeartbeatTrigger wake-on-diff-count, inotify diff accumulation.
- `codex_render.py` keeps: supermap rendering from CODEX.codex, coordinate resolution, any status/health endpoints.
- Cockpit plugin simplification: instead of requesting formatted diffs from the render engine, it calls `git diff` directly on the RAM worktree (or disk repo) and injects raw output as F labels.

## Migration
- Existing decisions `r-f-label-split-by-agent-role` and `diff-triggered-heartbeat-architecture` are **superseded** by this decision.
- The `diffentry-content-field-for-f-label-display` lesson is archived — no longer needed without formatted F labels.

## Related
- supersedes: r-f-label-split-by-agent-role
- supersedes: diff-triggered-heartbeat-architecture
- upstream: codex-engine-v2-live-diff-architecture
- related: ram-git-worktree-bootstrap (t20)
- related: ram-git-diff-pipeline (t21)
- related: ram-git-undo-primitive (t23)
