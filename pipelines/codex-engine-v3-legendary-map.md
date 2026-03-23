---
primitive: pipeline
status: phase1_complete
priority: critical
type: research
version: codex-engine-v3-legendary-map
spec_file: machinelearning/snn_applied_finance/specs/codex-engine-v3-legendary-map_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_codex-engine-v3-legendary-map.ipynb
agents: [architect, critic, builder]
supersedes: codex-engine-v2-modes
tags: [codex-engine, legendary-map]
project: codex
started: 2026-03-23
---

# Implementation Pipeline: CODEX-ENGINE-V3-LEGENDARY-MAP

## Description
LM namespace auto-generated action grammar and workflow sub-indices

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_codex-engine-v3-legendary-map.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-23 | belam-main | Pipeline instance created |
| pipeline_created | 2026-03-23 | belam-main | Pipeline created: LM namespace auto-generated action grammar and workflow sub-indices |
| architect_design | 2026-03-23 | architect | In progress |
| architect_design | 2026-03-23 | architect | Design complete: codex_lm_renderer.py (~250L) auto-generates lm namespace from modes/, commands/, render verbs, tool patterns. Dot-syntax sub-indices (e0.l1) for complex workflows. ~20L engine integration. 1KB budget. Graceful degradation. 4 open questions for critic. |
| architect_design | 2026-03-23 | architect | Design complete: codex_lm_renderer.py (~250L), dot-syntax sub-indices, ~20L engine integration, 1KB budget, 4 open questions for critic. |
| architect_design | 2026-03-23 | architect | Design complete |
| architect_design | 2026-03-23 | architect | Design complete: codex_lm_renderer.py (~250L), dot-syntax sub-indices, ~20L engine integration, 1KB budget, 4 open questions for critic. |
| architect_design | 2026-03-23 | architect | Designed LM namespace: auto-generated from modes/*.md + LM_RENDER_VERBS constant + LM_TOOL_PATTERNS constant + commands with lm_include:true opt-in. 20 entries target, ~933 bytes inline. Format: lm{n} verb syntax (no right annotation). lm{n} zoom = full expanded entry. Sub-indices via {coord}.l{n} dot-syntax parsing in router with workflow sections in mode files. .v.l{n} for view-group workflows via constant. Budget enforcement trims command tier first. Cache via module-level dict + mtime check on modes/ and commands/. Auto-update hooks in e3 and e2 handlers. Inserted before SHOW_ORDER loop in render_supermap(). ~270 lines new code + 5 command frontmatter tags. |
| architect_design | 2026-03-23 | architect | Designed LM: auto-generated entries from modes/*.md + RENDER_VERBS/TOOL_PATTERNS constants + lm_include:true commands. 20 entries ~933 bytes. lm{n} zoom. Dot-syntax sub-indices via {coord}.l{n}. Cache+mtime invalidation. Hooks in e3/e2. First in supermap. ~270 lines new code. |
| architect_design | 2026-03-23 | architect | LM design complete. Auto-gen from modes+constants+opt-in commands. 20 entries, dot-syntax sub-indices, mtime cache, e3/e2 hooks. |
| architect_design | 2026-03-23 | architect | Design doc written: LM auto-generated namespace from modes+constants+opt-in commands, dot-syntax sub-indices, mtime cache, e3/e2 hooks, first in supermap, ~270 lines new code. |
| critic_design_review | 2026-03-23 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (2 HIGH, 1 MED), 2 LOW. FLAG-1 HIGH: SHOW_ORDER + pre-loop render = crash (get_primitives can't handle None directory). FLAG-2 HIGH: caching strategy contradicts between design doc (no cache) and pipeline summary (mtime cache). FLAG-3 MED: entry count 16 vs 20, budget math mismatch. All fixable with one-line architect clarifications. Builder can proceed. |
| critic_design_review | 2026-03-23 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (2 HIGH, 1 MED). FLAG-1: SHOW_ORDER crash on None dir. FLAG-2: cache vs no-cache contradiction. FLAG-3: entry count mismatch. |
| critic_design_review | 2026-03-23 | critic | APPROVED 0 BLOCKs 3 FLAGs |
| critic_design_review | 2026-03-23 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (2 HIGH, 1 MED). Review at pipeline_builds/codex-engine-v3-legendary-map_critic_design_review.md |
| builder_implementation | 2026-03-23 | builder | In progress |
| builder_implementation | 2026-03-23 | builder | LM implementation complete: codex_lm_renderer.py (~310L) + codex_engine.py (+46L) + workflow sections in 2 modes + 4 commands tagged. All 3 FLAGs + 2 LOWs addressed. 18 entries, 1015B budget, 1.7ms render. Commit 5e200f6f. |
| critic_code_review | 2026-03-23 | critic | approved: clean implementation, two minor non-blocking flags (dead code in scan_modes, workflow coord heuristic) |

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
- **Spec:** `snn_applied_finance/specs/codex-engine-v3-legendary-map_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/codex-engine-v3-legendary-map_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/codex-engine-v3-legendary-map_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/codex-engine-v3-legendary-map_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_codex-engine-v3-legendary-map.ipynb`
