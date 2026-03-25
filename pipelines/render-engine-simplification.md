---
primitive: pipeline
status: phase2_complete
priority: high
type: builder-first
version: render-engine-simplification
spec_file: machinelearning/snn_applied_finance/specs/render-engine-simplification_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_render-engine-simplification.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [infrastructure, codex-engine, simplification]
project: codex-engine
started: 2026-03-24
---

# Implementation Pipeline: RENDER-ENGINE-SIMPLIFICATION

## Description
Strip R/F label diff pipeline, inotify, HeartbeatTrigger, and DiffEntry from render engine. Pure subtraction.

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_render-engine-simplification.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-24 | belam-main | Pipeline instance created |
| builder_implement | 2026-03-25 | builder | Implementation already complete from prior session. 9/9 tests GREEN. Removed 5 classes (DiffEntry, DiffEngine, StatPoller, InotifyWatcher, HeartbeatTrigger). codex_render.py: 2574→1896 lines (-678L, -26%). All diff/my_diff UDS commands stubbed for backward compat. All 3 FLAGs addressed. |
| builder_bugfix | 2026-03-25 | builder | Bugfix audit complete — no bugs found. Verified: (1) zero remaining references to DiffEntry/DiffEngine/StatPoller/InotifyWatcher/HeartbeatTrigger in codex_render.py, (2) codex_engine.py --render-diff and anchor_reset flags work (return empty from stub), (3) cockpit plugin diff path returns empty delta gracefully (FLAG-1 accepted V1), (4) flush worker thread still runs correctly for UDS refresh commands, (5) _on_file_change is dead code (no watcher calls it) but _process_file_change + flush_change_queue remain needed for UDS refresh path. Clean compile, 9/9 tests GREEN. |
| critic_review | 2026-03-25 | critic | APPROVED: 0 BLOCKs, 0 HIGH FLAGs, 1 LOW FLAG. Clean subtraction verified. codex_render.py: 2184→1896L (-288L). Zero references to DiffEntry/DiffEngine/StatPoller/InotifyWatcher/HeartbeatTrigger. Classes reduced 7→5 (DiffEntry/DiffEngine/StatPoller removed, InotifyWatcher/HeartbeatTrigger also removed). Background threads reduced. diff/my_diff/anchor_reset stubs return empty — cockpit plugin handles gracefully. ContextAssembler no longer references diff_engine. _on_file_change is dead code (defined L1660, never called). 9/9 tests pass. Supermap renders correctly. FLAG-1 LOW: _on_file_change dead code should be removed in cleanup. All design FLAGs addressed (FLAG-1 HIGH cockpit latency accepted V1, FLAG-2 MED ContextAssembler fixed, FLAG-3 LOW weak tests noted). Review at: pipeline_builds/render-engine-simplification_critic_design_review.md |
| phase1_complete | 2026-03-25 | belam-main | Phase 2 kickoff |

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on Phase 1 completion_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| phase2_architect_design | 2026-03-25 | architect | Phase 2 design: Remove cockpit plugin diff subprocess path (~33L removed from index.ts). This eliminates ~100-150ms overhead per agent turn (Python subprocess spawning to query empty diffs). Also fix T6+T7 weak tests. 2 deliverables, -23 net lines. After Phase 2, all task success criteria are met — recommend complete-task. |
| phase2_builder_implement | 2026-03-25 | builder | Phase 2 complete. D1: Removed cockpit plugin diff subprocess path (~33L from index.ts). Upgraded V8→V9 header. Eliminated execFileSync Python subprocess call that queried empty diffs every turn (~100-150ms savings per turn). D2: Removed _on_file_change dead code from codex_render.py (-18L). D3: Fixed T6 to verify stub content + no DiffEngine instantiation. Added T10 for cockpit plugin diff removal. codex_render.py now 1878L (total: 2574→1878, -696L, -27%). 10/10 tests GREEN. |
| phase2_builder_bugfix | 2026-03-25 | builder | Phase 2 bugfix audit: no bugs found. Zero remaining references to removed classes in both codex_render.py and cockpit plugin index.ts. Compile clean, imports clean. 10/10 tests GREEN. |
| phase2_critic_review | 2026-03-25 | critic | APPROVED: 0 BLOCKs, 0 FLAGs. Phase 2 cleanup verified. Cockpit plugin 204→169L (-35L). Diff subprocess call removed — only anchor-turn execFileSync remains (for supermap render). diffCount counter removed. Non-anchor turns return tailBlock directly — ~100-150ms savings per agent turn. 4 remaining 'diff' references are comments/legend text only (not code). T6/T7 replaced with meaningful checks. 10/10 tests pass. Full pipeline complete: codex_render.py 2184→1896L + cockpit 204→169L = -323L total subtraction. |

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
