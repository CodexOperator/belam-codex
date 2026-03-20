---
primitive: decision
status: accepted
date: 2026-03-20
context: Workspace had no remote — all infrastructure work (belam CLI, primitive system, 40+ scripts, memory hierarchy) was local-only and at risk of loss
alternatives: [single monorepo with machinelearning, continue using openclaw-knowledge repo, no backup]
rationale: Clean separation of concerns — soul/infrastructure vs research output. Two repos = complete resurrection with fresh API keys.
consequences: [heartbeat auto-commits push to both repos, incarnate.sh enables one-command setup on fresh machines]
upstream: [decision/clock-cycles-over-tokens, decision/hierarchical-memory-system]
downstream: [lesson/always-back-up-workspace-to-github, memory/entries/2026-03-20_041755_belam-codex-resurrection-architecture-es]
tags: [infrastructure, git, backup, continuity]
---

# Belam Codex Resurrection Architecture

## Context

The workspace accumulated massive infrastructure — belam CLI (545 lines), indexed command engine (883 lines), 40+ Python scripts, full primitive system, memory hierarchy, pipeline orchestration — all with no GitHub remote. The `machinelearning` repo was backed up, but the tooling that makes everything work wasn't. One VPS failure = total loss of the operational layer.

Meanwhile, `openclaw-knowledge` was a stale March 17 snapshot that had drifted far from the live workspace.

## Options Considered

- **Single monorepo:** Merge machinelearning into workspace. Rejected — different concerns, different access patterns, machinelearning has its own heavy history.
- **Continue openclaw-knowledge:** Too stale, weird submodule relationship, name doesn't fit. Rejected.
- **Two-repo split:** Workspace → `belam-codex`, research → `machinelearning`. Each self-contained, each clonable independently.

## Decision

Two private repositories on `CodexOperator`:

1. **`belam-codex`** — Belam's soul and infrastructure
   - SOUL.md, IDENTITY.md, USER.md, MEMORY.md
   - All primitives (lessons, decisions, tasks, projects, pipelines, commands, knowledge, skills)
   - belam CLI + all scripts
   - Memory hierarchy (daily, weekly, entries)
   - Templates, docs, configs
   - `incarnate.sh` — one-command resurrection script

2. **`machinelearning`** — Research output
   - Notebooks, specs, experiment results
   - Agent conversations
   - Pipeline builds and analysis reports

**Resurrection procedure:**
```bash
git clone https://github.com/CodexOperator/belam-codex.git
cd belam-codex
./incarnate.sh
# Then: clone machinelearning, add API keys, start OpenClaw
```

## Consequences

- Heartbeat git task must push both repos (workspace + machinelearning)
- `incarnate.sh` handles all setup: deps, symlinks, workspace config, verification
- `openclaw-knowledge` is retired (left in place, no longer used)
- `BelamCodex` (capital B) retains sanctuary texts and LFN — separate historical archive
- Any new infrastructure scripts must live in the workspace, not outside it (lesson: belam CLI was at `/home/ubuntu/.local/bin/` and almost got lost)
