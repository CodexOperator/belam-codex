---
primitive: pipeline
status: phase1_code_review
priority: critical
version: build-equilibrium-snn
spec_file: machinelearning/snn_applied_finance/specs/build-equilibrium-snn_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_build-equilibrium-snn.ipynb
agents: [architect, critic, builder]
tags: [snn, architecture, streaming]
project: snn-applied-finance
started: 2026-03-17
---

# Implementation Pipeline: BUILD-EQUILIBRIUM-SNN

## Description
Shael's continuous spike streaming architecture with opponent-coded outputs and persistent state across candles

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_build-equilibrium-snn.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-17 | belam-main | Pipeline instance created |
| pipeline_created | 2026-03-17 | belam-main | Pipeline kickoff |
| pipeline_created | 2026-03-18 | belam-main | Pipeline kickoff |
| architect_design | 2026-03-18 | architect | In progress |
| pipeline_created | 2026-03-18 | belam-main | Auto-kicked by pipeline_autorun (gate open or stall recovery) |
| architect_design | 2026-03-18 | architect | Design v1: 21 experiments (12 primary + 4 ablation + 5 baseline). Dual tonic+phasic input pathways, TBPTT K=8, membrane readout (V4 lesson applied), warmup LR schedule, 500 epochs w/ patience=100 for grokking. Critical ablation EQ-ABL-03 (reset-per-candle) validates equilibrium paradigm. |
| architect_design | 2026-03-18 | architect | Design v1: 21 experiments (12 primary + 4 ablation + 5 baseline). Dual tonic+phasic input pathways, TBPTT K=8, membrane readout (V4 lesson applied), warmup LR schedule, 500 epochs w/ patience=100 for grokking. |
| critic_design_review | 2026-03-18 | critic | APPROVED with 6 FLAGS (no blocks). FLAG-1: LR lambda warmup starts at 0 not lr_min, cosine floors at 0 not lr_min — fix lambda or spec. FLAG-2: n_folds=3 insufficient for Sharpe claims — reframe as exploratory. FLAG-3: LSTM baseline training protocol unspecified — must match SNN TBPTT/LR/state protocol for fair comparison. FLAG-4: Random seeds missing. FLAG-5: Transaction cost application method unspecified (round-trip? on position change only?). FLAG-6: eval function has redundant thresholding — store raw probabilities instead. Checklist 11/14 pass. Strongest design to date — paradigm falsifiable via EQ-ABL-03. |
| architect_design | 2026-03-18 | architect | Design v1: 21 experiments (12 primary + 4 ablation + 5 baseline). Dual tonic+phasic input, TBPTT K=8, membrane readout, warmup LR, 500 epochs patience=100. |
| builder_implementation | 2026-03-18 | builder | In progress |
| critic_design_review | 2026-03-18 | critic | APPROVED with 6 FLAGS (no blocks). FLAG-1: LR lambda bug. FLAG-2: n_folds=3 can't support Sharpe claims. FLAG-3: LSTM baseline protocol unspecified. FLAG-4: No random seeds. FLAG-5: Cost application unclear. FLAG-6: Eval redundant thresholding. Checklist 11/14 pass. Strongest design to date. |
| builder_implementation | 2026-03-18 | builder | crypto_build-equilibrium-snn_predictor.ipynb: 65 cells (30 code, 35 markdown). 21 experiments: 12 primary (4 scales x direction/magnitude x T_per_candle), 4 ablations (tonic-only, phasic-only, reset-per-candle, K=1), 5 baselines (LSTM, LogReg, RF, Majority). All 6 Critic FLAGS implemented. Critical control EQ-ABL-03 validates paradigm. TBPTT K=8, membrane readout, BCEWithLogitsLoss, warmup LR, 500 epochs patience=100. |
| builder_implementation | 2026-03-18 | builder | Notebook complete: 65 cells, 21 experiments, all 6 FLAGS addressed |
| critic_code_review | 2026-03-18 | critic | APPROVED with 2 FLAGS (no blocks). FLAG-1: import json missing in cell 4, used in cell 6 — NameError at runtime. FLAG-2: McNemar test (cell 49) compares EQ-04 vs EQ-ABL-03 on different candles — persistent excludes 20 warmup candles, reset doesn't. Trim ABL-03 predictions to match. All 6 design flags verified as implemented. Checklist 22/24 pass. Clean implementation. |
| phase1_complete | 2026-03-18 | architect | Phase 1 complete. Critic code review APPROVED (22/24 checklist). 2 non-blocking FLAGS: (1) missing import json in cell 4, (2) McNemar candle alignment between persistent and reset models. Builder can fix in Phase 2. Notebook ready for Shael review. |
| critic_code_review | 2026-03-18 | critic | In progress |
| critic_code_review | 2026-03-18 | critic | APPROVED with 2 FLAGS. FLAG-1: import json missing (cell 4→6 NameError). FLAG-2: McNemar compares different candles (warmup mismatch). All 6 design flags verified. 22/24 checklist pass. |
| critic_code_review_blocked | 2026-03-18 | critic | BLOCKED: BLOCK-1: json import missing before Cell 6 (imported in Cell 31, used in Cell 6 — NameError crash). 7 FLAGS (feature mismatch, seed reproducibility, bootstrap method, membrane visualization, misleading membrane_stats, McNemar header, magnitude pooled metrics). All 6 design FLAGS properly addressed. Fix BLOCK-1 (move import json to Cell 4), then ready to run. |
| code_review_fixes | 2026-03-18 | builder | Applied both Critic flags: (1) Added import json to Cell 5 — was NameError at Cell 6. (2) Fixed McNemar ABL-03 warmup alignment in Cell 50 and Cell 62 — trimming warmup candles from reset-per-candle ablation to match persistent-state model evaluation window. All 3 fix sites verified. |
| builder_apply_blocks | 2026-03-18 | builder | In progress |
| builder_apply_blocks | 2026-03-18 | builder | Fixed BLOCK-1 (json import confirmed in Cell 4, removed redundant from Cell 31) + all 7 FLAGS: feature deviation documented, deterministic hashlib seeds, block bootstrap added, membrane_stats renamed, Bonferroni header fixed, direction_accuracy added to magnitude pooled. Committed fc3551b. |

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
- **Spec:** `snn_applied_finance/specs/build-equilibrium-snn_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/build-equilibrium-snn_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/build-equilibrium-snn_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/build-equilibrium-snn_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_build-equilibrium-snn.ipynb`
