---
primitive: pipeline
status: phase1_build
priority: critical
type: research
version: codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing
spec_file: machinelearning/snn_applied_finance/specs/codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing.ipynb
agents: [architect, critic, builder]
supersedes:
tags: [snn, finance]
project: snn-applied-finance
started: 2026-03-23
---

# Implementation Pipeline: CODEX-ENGINE-V4-RAM-FIRST-RENDER-RUNTIME-WITH-NATIVE-CODEX-PARSING

## Description
codex engine v4 ram first render runtime with native codex parsing

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-23 | belam-main | Pipeline instance created |
| architect_design | 2026-03-23 | architect | Design v1: RAM-first render runtime. 7 deliverables (~240L net across 4 files). D1: write+create UDS commands with auto-flush to disk. D2: .codex snapshot hydration on startup (~5 lines). D3: ping/pong + my_diff UDS extensions. D4: cockpit plugin UDS-only path (180× speedup: ~900ms→~5ms first turn, ~350ms→~2ms subsequent). D5: engine reads from RAM (resolve_coords, render_supermap). D6: test mode flush suppression (3 lines). D7: per-node concurrency locks. No HTTP API, no .codex versioning, dulwich stays. 4 open questions for critic. |
| critic_design_review | 2026-03-23 | critic | APPROVED: 0 BLOCKs, 2 FLAGs (1 MED, 1 LOW). FLAG-1 MED: snapshot freshness check doesn't detect file deletions — ghost nodes persist in RAM. Fix: add file-count comparison. FLAG-2 LOW: no retry for failed disk flushes. All 4 open questions answered (sync flush correct, no snapshot versioning, 0.35s rebuild acceptable, async already supported in plugin). Clean write-through cache pattern, per-node locking correct, 180x speedup plausible. Review at: pipeline_builds/codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing_critic_design_review.md |

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
- **Spec:** `snn_applied_finance/specs/codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_codex-engine-v4-ram-first-render-runtime-with-native-codex-parsing.ipynb`
