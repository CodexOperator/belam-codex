---
primitive: pipeline
status: phase1_build
priority: high
type: infrastructure
version: pipeline-verification-phase-with-auto-fork-and-wiggum-test-loop
agents: [architect, critic, builder]
supersedes:
tags: [infrastructure, testing, verification, wiggum]
project: agent-roster
started: 2026-03-24
---

# Implementation Pipeline: PIPELINE-VERIFICATION-PHASE-WITH-AUTO-FORK-AND-WIGGUM-TEST-LOOP

## Description
Auto-fork on pipeline launch, architect test specs, builder wiggum verification loop, auto-merge on green

## Type
Infrastructure pipeline — no notebook, no experiment. Deliverables are code, hooks, plugins, and config files.
At phase1_complete, this pipeline is ready for human review and archival (no experiment/analysis phases).

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-24 | belam-main | Pipeline instance created |
| architect_design | 2026-03-24 | architect | Design v1: 7 deliverables (~190L, 2 files). D1: auto-fork git branch per pipeline (create/checkout/merge). D4: pipeline_verify.py test runner (~120L) — parses test_spec.md, runs automated/file-check/import-check tests, writes results. D5: wiggum steer integration for builder verification loop (5 iterations max). D7: STAGE_FLOW updated with builder_verification between implementation and code review. Self-referential: this design INCLUDES its own test spec (7 tests covering all deliverables). Concurrent pipeline branch conflict is the main risk — V1 uses sequential stash/checkout. 4 open questions for critic. |
| critic_design_review | 2026-03-24 | critic | APPROVED: 0 BLOCKs, 2 HIGH FLAGs, 2 MED FLAGs, 2 LOW FLAGs. FLAG-1 HIGH: concurrent branch race — fire_and_forget_dispatch is async (Popen), stash+checkout has no lock, two concurrent pipelines will clobber each other. Need fcntl.flock or defer branching to V2. FLAG-2 HIGH: fire_and_forget_dispatch returns {success,pid,error} not session_key — wiggum steer can't send without it. Fix: use generate_stage_session_id(). FLAG-3 MED: T4/T5 test raw git not actual functions. FLAG-4 MED: stash never popped — orphaned stash accumulates. FLAG-5 LOW: max_iterations dead code. FLAG-6 LOW: auto-commit cron referenced but not found. SUGGESTION: defer D1 branching to V2, ship D4+D5+D7 (verification loop) first. Review at: pipeline_builds/pipeline-verification-phase-with-auto-fork-and-wiggum-test-loop_critic_design_review.md |

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
- **Spec:** `snn_applied_finance/specs/pipeline-verification-phase-with-auto-fork-and-wiggum-test-loop_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/pipeline-verification-phase-with-auto-fork-and-wiggum-test-loop_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/pipeline-verification-phase-with-auto-fork-and-wiggum-test-loop_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/pipeline-verification-phase-with-auto-fork-and-wiggum-test-loop_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_pipeline-verification-phase-with-auto-fork-and-wiggum-test-loop.ipynb`
