---
primitive: pipeline
status: phase1_build
priority: high
version: research-openclaw-internals
spec_file: machinelearning/snn_applied_finance/specs/research-openclaw-internals_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_research-openclaw-internals.ipynb
agents: [architect, critic, builder]
tags: [research, openclaw]
project: multi-agent-infrastructure
started: 2026-03-21
---

# Implementation Pipeline: RESEARCH-OPENCLAW-INTERNALS

## Description
Research-OpenClaw-internals-session-routing-hooks-extension-points

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_research-openclaw-internals.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-21 | belam-main | Pipeline instance created |
| pipeline_created | 2026-03-21 | belam-main | Pipeline created: Research-OpenClaw-internals-session-routing-hooks-extension-points |
| architect_design | 2026-03-21 | architect | Completed infrastructure research design: mapped OpenClaw session routing (key construction, binding resolution, DM scopes), two-layer hook system (internal event scripts + plugin lifecycle hooks), full plugin registration API, and agent loop lifecycle with all hook injection points. Identified 5 concrete opportunities: (1) pipeline-context injection via before_prompt_build plugin hook [HIGH], (2) agent turn logging [MEDIUM], (3) native orchestrator tool plugin [HIGH], (4) bootstrap file hook for pipeline state [MEDIUM], (5) auto-reply pipeline commands [LOW-MEDIUM]. Design doc at pipeline_builds/research-openclaw-internals_architect_design.md. |
| architect_design | 2026-03-21 | architect | Design complete - mapped OpenClaw session routing, hooks, plugins, identified 5 improvement opportunities |
| architect_design | 2026-03-21 | architect | Design complete - mapped OpenClaw session routing, hooks, plugins, identified 5 improvement opportunities |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (1 medium, 2 low). All architectural claims verified accurate against OpenClaw docs. FLAG-1 (MED): lifecycle diagram should distinguish internal hooks vs plugin hooks. FLAG-2 (LOW): registerHook vs api.on() distinction needed. FLAG-3 (LOW): workspace plugins disabled by default not mentioned. Solid reference document. Review at: pipeline_builds/research-openclaw-internals_critic_design_review.md |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 3 FLAGs (1 med, 2 low). Verified against docs. Review at: pipeline_builds/research-openclaw-internals_critic_design_review.md |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (1 medium, 3 low). Accurate infrastructure reference — session routing, two-layer hook system, plugin API, agent loop lifecycle all verified against OpenClaw docs. FLAG-1 (MED): hook naming convention difference (colons vs underscores) not called out. FLAG-2 (LOW): reserved command names check needed. FLAG-3 (LOW): registerContextEngine opportunity not explored. FLAG-4 (LOW): message:preprocessed event missing. Opportunities correctly prioritized — before_prompt_build pipeline-context plugin is highest leverage. Review at: pipeline_builds/research-openclaw-internals_critic_design_review.md |
| critic_design_review | 2026-03-21 | critic | APPROVED: 0 BLOCKs, 4 FLAGs (1 med, 3 low). Review at: pipeline_builds/research-openclaw-internals_critic_design_review.md |
| builder_implementation | 2026-03-21 | builder | In progress |

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
- **Spec:** `snn_applied_finance/specs/research-openclaw-internals_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/research-openclaw-internals_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/research-openclaw-internals_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/research-openclaw-internals_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_research-openclaw-internals.ipynb`
