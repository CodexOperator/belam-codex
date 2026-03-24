---
primitive: pipeline
status: phase1_build
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

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on Phase 1 completion_

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
