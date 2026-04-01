---
primitive: pipeline
status: p1_complete
priority: high
type: builder-first
version: snn-deep-analysis-advanced-v3-v4
spec_file: machinelearning/snn_applied_finance/specs/snn-deep-analysis-advanced-v3-v4_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_snn-deep-analysis-advanced-v3-v4.ipynb
agents: [architect, critic, builder]
supersedes: 
tags: [snn, research, analysis, deep-dive]
project: snn-applied-finance
started: 2026-03-31
pending_action: p1_complete
current_phase: 
dispatch_claimed: false
last_updated: 2026-04-01 01:03
reset: false
---
# Implementation Pipeline: SNN-DEEP-ANALYSIS-ADVANCED-V3-V4

## Description
Deep research analysis of advanced SNN notebooks (V3, V4 autonomous, V4 combined). Three encoding schemes (popcode/delta/equilibrium), differential opponent output, magnitude decoding. Executable Python scripts generating rich visualizations. Illustrated research report.

## Builder Instructions

**This is NOT a notebook pipeline.** The builder should:

1. **Read the reference analysis** at `machinelearning/snn_applied_finance/research/deep_analysis/02_advanced_v3_v4.md` — this contains the raw research extracted from the notebooks
2. **Read the actual source notebooks** (extract key code cells):
   - `machinelearning/llm-quant-finance/notebooks/snn_crypto_predictor_v3.ipynb`
   - `machinelearning/llm-quant-finance/notebooks/snn_crypto_predictor_v4_autonomous.ipynb`
   - `machinelearning/llm-quant-finance/notebooks/snn_crypto_predictor_v4_combined.ipynb`
3. **Write Python visualization scripts** in `machinelearning/snn_applied_finance/research/deep_analysis/advanced_v3_v4/`:
   - `01_three_encodings_viz.py` — Side-by-side comparison of population coding, delta encoding, equilibrium encoding on the same synthetic signal
   - `02_differential_output_viz.py` — UP/DOWN neuron competition, spike rate differential, linear vs exponential vs magnitude decoding
   - `03_scale_comparison_viz.py` — Architecture diagrams for nano-5 through large-3200, parameter count scaling
   - `04_cost_function_evolution_viz.py` — V1 CrossEntropy → V4 BCE/Huber, learnable_scale effect, loss surface comparison
   - `05_dead_network_viz.py` — Spike rate analysis: healthy vs dead vs saturated networks, surrogate gradient shape
   - `06_equilibrium_mode_viz.py` — Cold-start vs warm-start inference, membrane state carry-over visualization
4. **Execute all scripts** — run each `.py` file, save output PNGs
5. **Compile final report** — `REPORT.md` in the same directory, embedding all generated figures with analysis text

**Key constraint:** Scripts must be self-contained (no GPU required, use synthetic/example data). Use matplotlib, seaborn, numpy, torch (CPU only).

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-31 | belam-main | Pipeline instance created |
| p1_builder_implement | 2026-03-31 | builder | Built 6 visualization scripts + REPORT.md for advanced V3/V4 SNN analysis |
| p1_builder_bugfix | 2026-03-31 | builder | Fixed 3 bugs: removed dead subplot loop in 03, fixed FancyBboxPatch name clobber in 04, removed emoji glyph causing font warning in 06. All 6 PNGs regenerated clean. |
| p1_critic_review | 2026-03-31 | critic | APPROVED: 0 BLOCKs, 0 FLAGs. All 6 scripts execute clean, math is correct (LIF dynamics, surrogate gradients, parameter counting, loss formulas). Bug fixes verified. REPORT.md well-structured. 2 minor suggestions: unify box styles across scripts, note data-dependence of exponential decoding bounds. |
| p1_builder_implement | 2026-04-01 | architect | Analysis complete, reports and visualizations on disk. Closing pipeline. |
| p1_builder_bugfix | 2026-04-01 | builder | Applied portability fix: all 6 scripts now use SCRIPT_DIR relative to __file__ instead of hardcoded workspace paths. Verified runnable from /tmp. Critic had already approved with 0 BLOCKs, 0 FLAGs. All 6 PNGs regenerated clean. |
| p1_critic_review | 2026-04-01 | critic | APPROVED: Portability fix verified — all 6 scripts use SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) consistently, no hardcoded paths remain. Confirmed runnable from /tmp. No regressions from prior clean review (0 BLOCKs, 0 FLAGs). PNGs regenerate clean. |

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
- **Spec:** `snn_applied_finance/specs/snn-deep-analysis-advanced-v3-v4_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/snn-deep-analysis-advanced-v3-v4_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/snn-deep-analysis-advanced-v3-v4_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/snn-deep-analysis-advanced-v3-v4_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_snn-deep-analysis-advanced-v3-v4.ipynb`
