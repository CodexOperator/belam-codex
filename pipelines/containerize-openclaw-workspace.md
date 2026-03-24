---
primitive: pipeline
status: phase1_complete
priority: high
type: infrastructure
version: containerize-openclaw-workspace
agents: [architect, critic, builder]
supersedes:
tags: [snn, finance]
project: snn-applied-finance
started: 2026-03-24
---

# Implementation Pipeline: CONTAINERIZE-OPENCLAW-WORKSPACE

## Description
Container runtime isolation for OpenClaw workspace

## Type
Infrastructure pipeline — no notebook, no experiment. Deliverables are code, hooks, plugins, and config files.
At phase1_complete, this pipeline is ready for human review and archival (no experiment/analysis phases).

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-24 | belam-main | Pipeline instance created |
| architect_design | 2026-03-24 | architect | Design v1: Single-container Docker deployment. 7 files (~150L). D1: Dockerfile (node:22-bookworm-slim, Python3+pip, openclaw npm, UID-matching for bind mounts). D2: docker-compose.yml with bind-mounted ~/.openclaw. D3: requirements.txt (torch, snntorch, scipy, numpy, PyYAML, dulwich). D5: build/run/stop shell scripts. D6: migration guide. ARM64-native (no cross-compile). Gateway runs foreground as PID 1. Workspace files bind-mounted for persistence. Test spec: 6 tests. 4 open questions for critic (Docker not installed on host, --foreground flag, render engine, Telegram polling vs webhook). |
| critic_design_review | 2026-03-24 | critic | APPROVED: 0 BLOCKs, 3 HIGH FLAGs, 1 MED FLAG, 1 LOW FLAG. FLAG-1 HIGH: Entrypoint 'openclaw gateway start --foreground' does not exist — use 'openclaw gateway run' (verified via --help). FLAG-2 HIGH: Bind-mounting ~/.npm-global creates circular dependency with container's npm install — remove the mount, container should be self-contained. FLAG-3 HIGH: torch>=2.10.0 is ~2.4GB on ARM64 and not needed for gateway/infrastructure agents — split into requirements-base.txt and requirements-ml.txt, use base only. FLAG-4 MED: No .env file — docker compose variables need defaults. FLAG-5 LOW: T1 uses docker build --check which may not exist. Also: Telegram confirmed as polling (not webhook), render engine works via bind mount, Docker not installed on host (prerequisite in D6). Review at: pipeline_builds/containerize-openclaw-workspace_critic_design_review.md |
| builder_implementation | 2026-03-24 | builder | All 6 deliverables implemented. D1 Dockerfile: ARM64 node:22-bookworm-slim, gateway run entrypoint (FLAG-1), UID/GID matching. D2 docker-compose.yml: single container, no npm-global mount (FLAG-2), log rotation. D3 requirements split: base (~600MB) vs ml (~3GB) (FLAG-3). D4 .dockerignore. D5 build/run/stop scripts with auto .env generation (FLAG-4). D6 migration guide with rollback. Test spec 9/9 GREEN. Docker not installed on host — tests are file/content checks only, integration tests need Docker install first. |
| builder_verification | 2026-03-24 | builder | GREEN: 9/9 tests passed. T1-T9 all PASS covering Dockerfile, compose, requirements split, dockerignore, scripts, migration guide, entrypoint fix, and npm-global fix. |
| critic_code_review | 2026-03-24 | critic | APPROVED: 0 BLOCKs, 0 HIGH FLAGs, 1 MED FLAG, 1 LOW FLAG. All 3 design HIGH FLAGs resolved (entrypoint uses 'gateway run', no npm-global mount, requirements split into base/ml). 9/9 tests pass. FLAG-1 MED: tests use relative paths — only work from main workspace CWD, not agent workspaces. FLAG-2 LOW: stale docker/ directory alongside new root-level files. 7 files, ~275L total. Clean, minimal, well-documented with rollback path. Review at: pipeline_builds/containerize-openclaw-workspace_critic_code_review.md |
| phase1_complete | 2026-03-24 | architect | Phase 1 COMPLETE. Critic code review APPROVED 0 BLOCKs, 2 FLAGs (1 MED, 1 LOW). All 3 design HIGH FLAGs resolved (entrypoint uses 'gateway run', no npm-global mount, requirements split base/ml). 9/9 tests pass. 7 files, 275L. FLAG-1 MED: tests use relative paths (only work from main workspace CWD). FLAG-2 LOW: stale docker/ directory. Ready for Shael review — Docker not yet installed on host, so container hasn't been live-tested. |
| phase1_complete | 2026-03-24 | main | Archived via heartbeat |
| phase1_complete | 2026-03-24 | main | Archived via heartbeat (09:48) |
| phase1_complete | 2026-03-24 | main | Archived via heartbeat (10:18) |
| phase1_complete | 2026-03-24 | main | Archived via heartbeat (10:48) |
| phase1_complete | 2026-03-24 | main | Archived via heartbeat (11:18) |
| phase1_complete | 2026-03-24 | main | Archived |
| phase1_complete | 2026-03-24 | main | Heartbeat archive |
| phase1_complete | 2026-03-24 | main | Heartbeat archive |
| phase1_complete | 2026-03-24 | main | Heartbeat archive |

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on Phase 1 completion_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| phase2_architect_design_blocked | 2026-03-24 | architect | BLOCKED: BLOCK: No Phase 2 direction from Shael. Docker is not installed on host — Phase 2 requires Shael to install Docker, then provide direction for live testing and migration from systemd. Unblock by creating phase2_direction.md. |

### Feedback
_(Shael's feedback goes here when Phase 1 is complete and reviewed)_

## Phase 3: Iterative Research (Autonomous or Human-Triggered)
_Status: LOCKED — requires Phase 2 completion before activation_

**Gate condition:** `phase2_complete` must be set before any Phase 3 iteration can proceed.

### How Phase 3 Works

1. **Human-triggered:** Shael says "try X" → iteration created and built
2. **Agent-triggered:** Analysis reveals compelling follow-up → proposal generated:
   - Score ≥ 7: auto-approved
   - Score 4-6: flagged for Shael's review
   - Score < 4: rejected, logged only

### Iteration Log

| ID | Hypothesis | Proposed By | Status | Result |
|----|-----------|-------------|--------|--------|

## Artifacts
- **Spec:** `snn_applied_finance/specs/containerize-openclaw-workspace_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/containerize-openclaw-workspace_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/containerize-openclaw-workspace_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/containerize-openclaw-workspace_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_containerize-openclaw-workspace.ipynb`
