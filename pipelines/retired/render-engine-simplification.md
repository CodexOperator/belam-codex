---
primitive: pipeline
status: phase1_build
archived: 2026-03-24
archive_reason: "Killed — orchestrator used default transitions instead of builder-first. Template not yet wired into pipeline_orchestrate.py."
priority: high
type: builder-first
version: render-engine-simplification
agents: [builder, critic, architect]
supersedes:
tags: [codex-engine, simplification, infrastructure]
project: codex-engine
started: 2026-03-24
---

# Implementation Pipeline: RENDER-ENGINE-SIMPLIFICATION

## Description
Strip R/F label diff pipeline, inotify, HeartbeatTrigger, and DiffEntry from render engine. Pure subtraction — no new features.

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_render-engine-simplification.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-24 | belam-main | Pipeline instance created |
| pipeline_created | 2026-03-24 | belam-main | Launching builder-first pipeline. Task spec is fully defined in tasks/render-engine-simplification.md |
| architect_design | 2026-03-24 | architect | Design v1: Pure subtraction — remove DiffEntry, DiffEngine, StatPoller from codex_render.py. 3 classes deleted (~211L), ~314L total reduction (2184→~1870). 10-step bottom-up deletion order. Background threads reduced 2→1 (no more 500ms polling). Diff/my_diff UDS commands stubbed (return empty) for backward compat. 7 tests covering class removal + supermap preservation. 3 open questions for critic. Builder-first pipeline — spec is fully defined, this design validates approach. |
| critic_design_review | 2026-03-24 | critic | APPROVED: 0 BLOCKs, 1 HIGH FLAG, 1 MED FLAG, 1 LOW FLAG. FLAG-1 HIGH: cockpit plugin still runs execFileSync for diff every turn (~100-150ms) even though diffs will always be empty after removal. Should remove the diff path from plugin (Option A) or accept latency (Option B). Affects every agent turn continuously. FLAG-2 MED: ContextAssembler uses diff_engine.get_delta() at lines 1647+1679 — must replace with empty string or remove delta section entirely, not just delete the parameter. FLAG-3 LOW: T6 is a tautology (prints PASS without testing), T7 tests R/F labels unrelated to simplification. Line counts verified: DiffEntry L86 ~8L, DiffEngine L683 ~108L, StatPoller L792 ~95L. 65 diff-related references to clean. Bottom-up deletion order correct. Stub approach for UDS diff command correct. Review at: pipeline_builds/render-engine-simplification_critic_design_review.md |

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
- **Spec:** `snn_applied_finance/specs/render-engine-simplification_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/render-engine-simplification_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/render-engine-simplification_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/render-engine-simplification_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_render-engine-simplification.ipynb`
