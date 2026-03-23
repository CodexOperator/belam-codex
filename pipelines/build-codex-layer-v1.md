---
primitive: pipeline
status: phase1_complete
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
