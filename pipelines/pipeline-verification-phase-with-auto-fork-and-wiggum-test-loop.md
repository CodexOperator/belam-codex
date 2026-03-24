---
primitive: pipeline
status: archived
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
| builder_implementation | 2026-03-24 | builder | Implemented D4+D5+D7 (verification loop). D1 branching deferred to V2 per critic suggestion. pipeline_verify.py: 230L test runner with parse/run/report. dispatch_verification: uses generate_stage_session_id for deterministic session routing + wiggum steer timer. STAGE_FLOW/STAGE_TRANSITIONS updated for both Phase 1 and Phase 2. Self-referential test spec passes 8/8. All 6 FLAGs addressed. |
| builder_verification | 2026-03-24 | builder | GREEN: 8/8 tests passed, 0 failed, 0 skipped. T1: STAGE_FLOW routing ✅ T2: STAGE_TRANSITIONS routing ✅ T3: Test spec parser ✅ T4: Test runner pass/fail ✅ T5: Manual test skip ✅ T6: Missing spec graceful ✅ T7: dispatch_verification + session_id ✅ T8: Dry-run mode ✅. Results at pipeline_builds/pipeline-verification-phase-with-auto-fork-and-wiggum-test-loop_test_results.md |
| critic_code_review | 2026-03-24 | critic | APPROVED: 0 BLOCKs, 1 MED FLAG, 1 LOW FLAG. All 6 design FLAGs resolved (D1 branching deferred — best resolution). 8/8 tests pass (verified independently). FLAG-1 MED: check_pass_criteria passes on non-zero exit when criteria only says 'contains' without 'exit code 0' — default should require exit 0. FLAG-2 LOW: T8 checklist description mismatch. 300L pipeline_verify.py clean, dispatch_verification uses generate_stage_session_id correctly, STAGE_FLOW and STAGE_TRANSITIONS both updated. Review at: pipeline_builds/pipeline-verification-phase-with-auto-fork-and-wiggum-test-loop_critic_code_review.md |
| phase1_complete | 2026-03-24 | architect | Phase 1 COMPLETE. Critic code review APPROVED 0 BLOCKs, 2 FLAGs (1 MED, 1 LOW). All 6 design FLAGs resolved (D1 branching deferred — correct decision). 8/8 tests pass. 300L pipeline_verify.py + STAGE_FLOW/STAGE_TRANSITIONS updated. FLAG-1 MED: check_pass_criteria should default to requiring exit code 0 when criteria only says 'contains'. FLAG-2 LOW: T8 checklist description mismatch. Ready for Phase 2 human review. |
| phase1_complete | 2026-03-24 | belam-main | Phase 2 kickoff. Direction at pipeline-verification-phase-with-auto-fork-and-wiggum-test-loop_phase2_direction.md |

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on Phase 1 completion_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| phase2_architect_design_blocked | 2026-03-24 | architect | BLOCKED: BLOCK: No Phase 2 direction from Shael. Phase 2 requires human review of Phase 1 and direction for what to add (e.g. git branching via worktree, research pipeline test specs, integration with existing pipelines). Unblock by creating phase2_direction.md. |
| phase2_architect_design | 2026-03-24 | architect | Phase 2 design: 3 deliverables (~135L, 3 files). D1: git worktree isolation — each pipeline gets /tmp/pipeline-{version}/ directory, zero contention between concurrent pipelines, merge back on complete. D9: verification auto-retry — max 3 re-dispatches on failure, audit trail in test_results.md, escalate to coordinator on exhaustion. D8: lesson injection verification + diagnostic flag. Opt-in via use_worktree:true in state JSON. 3 new tests (T9-T11). 4 open questions for critic. |
| phase2_critic_design_review | 2026-03-24 | critic | APPROVED: 0 BLOCKs, 2 HIGH FLAGs, 1 MED FLAG, 1 LOW FLAG. FLAG-1 HIGH: D9 dispatch_verification() rewrite regresses Phase 1 FLAG-2 fix — uses result.get('session_key') instead of generate_stage_session_id(). Must preserve existing fix. FLAG-2 HIGH: Agent CWD vs agent workspace mismatch — openclaw agent resolves workspace from config, not Popen cwd. Worktree may create directories agents never use. Builder must verify if --workspace flag exists or accept worktree as branch-isolation-only. FLAG-3 MED: T11 tests arithmetic not actual retry code. FLAG-4 LOW: append mode in write_results unbounded but small. SUGGESTION: Ship D9+D8 first, defer D1 worktree until CWD routing verified. Review at: pipeline_builds/pipeline-verification-phase-with-auto-fork-and-wiggum-test-loop_phase2_critic_design_review.md |
| phase2_builder_implementation | 2026-03-24 | builder | Phase 2 implemented: D9 (auto-retry verification loop, max 3 retries with escalation), D8 (lesson injection diagnostic via show-lessons subcommand). D1 (git worktree) deferred — agent workspace routing unresolved (FLAG-2 HIGH). All FLAGs addressed: FLAG-1 preserved generate_stage_session_id, FLAG-2 documented worktree limitation, FLAG-3 T9-T11 test actual code not arithmetic, FLAG-4 noted in docstring. 11/11 tests GREEN. |
| phase2_builder_verification | 2026-03-24 | builder | GREEN: 11/11 tests passed. T1-T8 (Phase 1 core) + T9 (auto-retry logic) + T10 (retry counter) + T11 (show_lessons). All pass. |
| phase2_critic_code_review | 2026-03-24 | critic | APPROVED: 0 BLOCKs, 1 HIGH FLAG, 1 MED FLAG. All 4 design FLAGs resolved (D1 worktree deferred, session_key fix preserved, T11 improved, append mode not implemented). FLAG-1 HIGH: check_verification_result uses substring 'green' in notes — false positive on 'greenfield' test names, false negative on '11/11 passed' (hardcoded '8/8'). Fix: parse test_results.json directly instead of string matching notes. FLAG-2 MED: Phase 1 check_pass_criteria exit code gap still unfixed (not in scope). 11/11 tests pass. D9 auto-retry clean, D8 show_lessons clean. Review at: pipeline_builds/pipeline-verification-phase-with-auto-fork-and-wiggum-test-loop_phase2_critic_code_review.md |
| phase2_complete | 2026-03-24 | architect | Phase 2 COMPLETE. Critic code review APPROVED 0 BLOCKs, 2 FLAGs (1 HIGH, 1 MED). 11/11 tests pass. D1 worktree deferred (correct — validate retry loop first). D9 auto-retry clean. D8 show_lessons clean. FLAG-1 HIGH: check_verification_result uses substring matching on notes — should parse test_results.json directly. FLAG-2 MED: Phase 1 check_pass_criteria exit code default gap (carried forward). Both FLAGs are non-blocking but should be fixed before heavy production use of the verification loop. |
| phase2_complete | 2026-03-24 | main | Archived via heartbeat |
| phase2_complete | 2026-03-24 | main | Archived via heartbeat (11:18) |
| phase2_complete | 2026-03-24 | main | Archived via heartbeat (11:18) |
| phase2_complete | 2026-03-24 | main | Heartbeat archive |
| phase2_complete | 2026-03-24 | main | Heartbeat archive |
| phase2_complete | 2026-03-24 | main | Heartbeat archive |
| phase2_complete | 2026-03-24 | main | Heartbeat archive |

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
