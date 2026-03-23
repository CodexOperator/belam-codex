---
primitive: pipeline
status: archived
priority: critical
type: research
version: build-codex-layer-v1
spec_file: machinelearning/snn_applied_finance/specs/build-codex-layer-v1_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_build-codex-layer-v1.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [codex-layer, infrastructure]
project: codex
started: 2026-03-23
archived: 2026-03-23
archived: 2026-03-23
---

# Implementation Pipeline: BUILD-CODEX-LAYER-V1

## Description
Codex Layer v1: programmatic coordinate guardrails — interceptor, output-codec, symbolic-dispatch

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_build-codex-layer-v1.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-23 | belam-main | Pipeline instance created |
| architect_design | 2026-03-23 | architect | Design complete: 3 new files (~585L total). D1 output codec with result register (_/_N/_.field), D2 symbolic dispatch (bare coords/.prefix/!shell/pipe>), D3 interceptor with 10 static rules + LM auto-rules + graduated enforcement (advisory→redirect→block). Advisory mode only for Phase 1. 4 open questions for critic. |
| critic_design_review | 2026-03-23 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (2 HIGH, 2 MED). FLAG-1 HIGH: register file globally shared — scope per-workspace. FLAG-2 HIGH: pipe ' > ' collides with shell redirect + dispatch ordering bug. FLAG-3 MED: _ coord carve-out needed. FLAG-4 MED: LM auto-rules speculative, stub for v1. Review at: pipeline_builds/build-codex-layer-v1_critic_design_review.md |
| builder_implementation | 2026-03-23 | builder | Codex Layer v1 complete: 3 new files (output codec 351L, dispatch 211L, interceptor 214L) + engine +50L + cockpit plugin +8L = 834 lines total. All 4 FLAGs addressed: register per-workspace (FLAG-1), |> pipes with ! prefix priority (FLAG-2), _ carve-out in resolve_coords (FLAG-3), LM auto-rules stubbed (FLAG-4). Advisory mode only for Phase 1. All suggestions incorporated (S1 --register-clear, S2 5min TTL, S3 noted). Commit 2706afcb. |
| critic_code_review | 2026-03-23 | critic | APPROVED: 0 BLOCKs, 2 FLAGs (1 HIGH, 1 MED). FLAG-1 HIGH: greedy _ substitution in pipe chains mangles underscored identifiers — one-liner fix needed before Phase 2. FLAG-2 MED: _lm_text dead data in resolve_coords (pre-existing LM pattern). All 4 design FLAGs resolved, all 3 suggestions incorporated. 834L clean implementation. Review at: pipeline_builds/build-codex-layer-v1_critic_code_review.md |
| phase1_complete | 2026-03-23 | architect | Phase 1 COMPLETE. Critic code review APPROVED 0 BLOCKs, 2 FLAGs (1 HIGH, 1 MED). 834L clean implementation across 3 new files (output codec 351L, dispatch 211L, interceptor 214L) + engine +50L + cockpit +8L. All 4 design FLAGs resolved. Outstanding: FLAG-1 greedy _ substitution in pipe chains (one-liner fix for Phase 2), FLAG-2 _lm_text dead data. Ready for Phase 2 human review. |

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on Phase 1 completion_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| phase2_architect_design | 2026-03-23 | architect | Phase 2 design: 4 priorities, ~158 lines across 4 files. P1: compound coord fix + FLAG fixes. P2: render engine auto-start + UDS diff injection + anchor reset. P3: conversational agent flow with session tracking, exchange limits (3), diff-based reviews, group chat visibility. P4: autonomous iteration cron every 35min with gate checks. 4 open questions for critic. |
| phase2_critic_design_review_blocked | 2026-03-23 | critic | BLOCKED: BLOCK-1 CRITICAL: P3 sessions_send not callable from orchestrator — architect must specify mechanism (Option A/B/C). P1/P2/P4 can proceed. 3 FLAGs (1 HIGH socket path, 1 MED _lm_text, 1 LOW iteration cap). Review: pipeline_builds/build-codex-layer-v1_phase2_critic_design_review.md |
| phase2_architect_revision | 2026-03-23 | architect | BLOCK-1 resolved: Option B (session-ID tracking via CLI) with Option C fallback. Builder fresh, critic resumes. Orchestrator-mediated sequential loop, max 3 exchanges. FLAG-1: workspace-scoped .codex_runtime/ dir for all artifacts. FLAG-2: keep _lm_text, add consumer in render_zoom. FLAG-3: max_total_unreviewed=6 cap. All 4 suggestions accepted. 184 lines across 5 files. |
| phase2_critic_design_review | 2026-03-23 | critic | APPROVED: 0 BLOCKs, 2 FLAGs (1 MED, 1 LOW). BLOCK-1 resolved: Option B (session-ID tracking via CLI) + Option C fallback. All original FLAGs addressed. NEW FLAG-1 MED: exchange loop needs per-dispatch timeout (300s). NEW FLAG-2 LOW: group chat 1-exchange dedup. Review at: pipeline_builds/build-codex-layer-v1_phase2_critic_design_review_r2.md |
| phase2_builder_implementation | 2026-03-23 | builder | Phase 2 complete: 360 lines across 7 files. P1: compound coord regex + greedy _ fix + _lm_text consumer + .codex_runtime/ convention. P2: render engine auto-start + UDS diff + anchor reset. P3: exchange loop with session-ID tracking, 300s timeout, diff reviews, group chat dedup. P4: --iterate with 4 gate checks + proposal logging. All FLAGs addressed. Commit d1c14508. |
| phase2_critic_code_review | 2026-03-23 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (1 MED, 2 LOW). All Phase 1+2 FLAGs resolved. FLAG-1 MED: P4 iteration counter never resets (daily_human_input never set, daily_iteration_count never reset). FLAG-2 LOW: single recv in get_render_diff. FLAG-3 LOW: dir() style. 360L, 7 files, all deliverables D1-D8+S3 verified. Review at: pipeline_builds/build-codex-layer-v1_phase2_critic_code_review.md |
| phase2_complete | 2026-03-23 | architect | Phase 2 COMPLETE. Critic code review APPROVED 0 BLOCKs, 3 FLAGs (1 MED iteration counter reset, 2 LOW). All Phase 1 FLAGs resolved (greedy _ substitution, _lm_text consumer). All Phase 2 design FLAGs resolved (dispatch timeout, group chat dedup). 360L across 7 files. P1: compound coord regex + .codex_runtime/ convention. P2: render engine auto-start + UDS diff + anchor reset. P3: Option B exchange loop (builder fresh, critic resumes via session-ID, max 3 exchanges). P4: autonomous iteration cron with 5 gate checks. Outstanding: FLAG-1 MED daily_iteration_count never resets and daily_human_input never set — P4 will silently stop after 3 iterations on day 1. Fix in Phase 3 or next pipeline. |

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
- **Spec:** `snn_applied_finance/specs/build-codex-layer-v1_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/build-codex-layer-v1_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/build-codex-layer-v1_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/build-codex-layer-v1_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_build-codex-layer-v1.ipynb`
