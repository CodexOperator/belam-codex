---
primitive: pipeline
status: archived
archived: 2026-03-24
archive_reason: Pipeline caused gateway shutdown and PATH loss. Stopped by Shael.
priority: high
type: infrastructure
version: container-build-and-test
agents: [architect, critic, builder]
supersedes: 
tags: [snn, finance]
project: snn-applied-finance
started: 2026-03-24
pending_action: builder_implementation
current_phase: 
dispatch_claimed: false
last_updated: 2026-03-24 15:53
reset: false
---
# Implementation Pipeline: CONTAINER-BUILD-AND-TEST

## Description
Build Docker image, verify gateway starts, write disaster recovery runbook

## Type
Infrastructure pipeline — no notebook, no experiment. Deliverables are code, hooks, plugins, and config files.
At phase1_complete, this pipeline is ready for human review and archival (no experiment/analysis phases).

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-24 | belam-main | Pipeline instance created |
| architect_design | 2026-03-24 | architect | Design v1: Container build and disaster recovery validation. 5 deliverables (~210L, 4-5 files). D1: Docker install script (requires sudo). D2: 11-test validation script (build→start→health→mounts→deps→CLI). D3: disaster recovery runbook (15-30 min recovery from complete VM loss). D4: container update workflow. D5: Dockerfile fixes discovered during build. Docker NOT installed on host — D1 is the gate. Builder must either have sudo or Shael installs Docker manually. 13 tests total. 4 open questions for critic. |
| critic_design_review | 2026-03-24 | critic | APPROVED: 0 BLOCKs, 2 HIGH FLAGs, 2 MED FLAGs, 1 LOW FLAG. FLAG-1 HIGH: systemd gateway on port 18789 — validation must stop it before container start and restart after tests. Use trap for cleanup on failure. FLAG-2 HIGH: config.yaml NOT in git (verified) — disaster recovery runbook incorrectly assumes it's preserved. Config at ~/.hermes/config.yaml is outside workspace, not tracked. Document separate backup requirement. FLAG-3 MED: docker compose exec tests need running-container guard. FLAG-4 MED: sleep 10 may not be enough for ARM64 cold start — use retry loop. FLAG-5 LOW: install script idempotency. Sudo works without password. openclaw gateway run confirmed correct. Q1: sudo OK. Q2: gateway run exists. Q3: non-destructive validation. Q4: CLI verify only, no dispatch. Review at: pipeline_builds/container-build-and-test_critic_design_review.md |

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
- **Spec:** `snn_applied_finance/specs/container-build-and-test_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/container-build-and-test_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/container-build-and-test_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/container-build-and-test_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_container-build-and-test.ipynb`
