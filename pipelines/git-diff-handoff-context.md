---
primitive: pipeline
status: p1_complete
priority: high
type: builder-first
version: git-diff-handoff-context
spec_file: machinelearning/snn_applied_finance/specs/git-diff-handoff-context_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_git-diff-handoff-context.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [snn, finance]
project: snn-applied-finance
started: 2026-03-25
archived: 2026-03-25
---

# Implementation Pipeline: GIT-DIFF-HANDOFF-CONTEXT

## Description
Add git-diff context to pipeline handoff messages — snapshot commit hashes at each stage transition, generate scoped diffs when building handoff context for returning agents

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_git-diff-handoff-context.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-25 | belam-main | Pipeline instance created |
| p1_builder_implement | 2026-03-25 | builder | Implemented handoff_diff.py with snapshot recording and scoped diff generation. Wired into pipeline_orchestrate.py complete/block flows. 17 tests all passing. |
| p1_builder_bugfix | 2026-03-25 | builder | Bugfix audit complete — no bugs found. 17/17 tests GREEN. Verified: (1) snapshot recording handles missing repos gracefully, (2) agent-specific snapshot lookup walks backwards correctly, (3) diff truncation at 3000 chars works, (4) ipynb filter excludes noisy notebook diffs, (5) handoff_snapshots key preserved through pipeline_update load/save cycles, (6) orchestrator integration wired into both complete and block flows with try/except fallback, (7) state file hierarchy consistent between handoff_diff and pipeline_update. |
| p1_critic_review | 2026-03-25 | critic | APPROVED: 0 BLOCKs, 0 HIGH FLAGs, 1 MED FLAG, 1 LOW FLAG. 17/17 tests GREEN (verified independently). 15 independent verifications passed. FLAG-1 MED: _has_ipynb checks substring in entire diff text (not filenames) — false positives possible when .py files reference .ipynb paths (e.g. handoff_diff.py's own docstring). Falls back to stat-only (less informative, not incorrect). FLAG-2 LOW: shared scripts (handoff_diff.py, pipeline_orchestrate.py) appear in all pipeline diffs. Implementation is clean: snapshot-then-diff pattern, agent-scoped lookups, graceful degradation, scoped paths. Orchestrator integration correct (step 0.5 before pipeline_update, try/except fallback). Review at: pipeline_builds/git-diff-handoff-context_critic_review.md |

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
- **Spec:** `snn_applied_finance/specs/git-diff-handoff-context_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/git-diff-handoff-context_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/git-diff-handoff-context_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/git-diff-handoff-context_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_git-diff-handoff-context.ipynb`
