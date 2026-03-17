---
primitive: analysis_pipeline
status: analysis_phase1_design
priority: high
version: v4-analysis
source_version: v4
source_pkl_dir: SNN_research/machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_v4_pkl/
output_notebook: SNN_research/machinelearning/snn_applied_finance/notebooks/crypto_v4_analysis.ipynb
agents: [architect, critic, builder]
tags: [snn, analysis, v4]
project: snn-applied-finance
started: 2026-03-17
---

# Analysis Pipeline: V4-ANALYSIS

## Description
Deep analysis of V4 differential output experiment results — 32 experiments across 6 groups testing spike-count readout, nano-to-medium scale networks, rate/delta/equilibrium encodings, direction vs magnitude output. Root cause analysis of dead-neuron failures, encoding comparison (invalidated by output confound), and architecture lessons for V5.

## Source Data
- **Source Version:** `v4`
- **Pkl Files:** `SNN_research/machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_v4_pkl/`
- **Upload Method:** Individual pkl files OR single zip — notebook handles both

## Notebook Convention
**Both analysis phases live in a single notebook** (`crypto_v4_analysis.ipynb`).
Phase 1 sections are autonomous statistical analysis; Phase 2 sections are appended after Shael's direction.

## Agent Coordination Protocol

**Filesystem-first:** All data exchange between agents happens via shared files, never through `sessions_send` message payloads.

| Action | Method | Example |
|--------|--------|---------|
| Share design/review/fix | Write file to `research/pipeline_builds/` | `v4-analysis_architect_analysis_design.md` |
| Track stage transitions | `python3 scripts/pipeline_update.py v4-analysis complete {stage} "{notes}" {agent}` | Auto-updates state JSON, markdown, pending_action |
| Block a stage (Critic) | `python3 scripts/pipeline_update.py v4-analysis block {stage} "{notes}" {agent} --artifact {file}` | Sets pending_action to fix step |
| Notify another agent | `sessions_send` with `timeoutSeconds: 0` | "Analysis design ready" |
| Update Shael / group | `message` tool to group chat | "Phase 1 analysis complete — 5 findings" |

**Never** use `sessions_send` with a timeout > 0. Write the file first, ping second.

### Pipeline Update Script — Mandatory Usage
Every stage transition MUST go through `pipeline_update.py`. Always follow its printed ping instructions.

## Phase 1: Autonomous Analysis
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-17 | belam-main | Analysis pipeline created |

## Phase 2: Directed Analysis (Human-in-the-Loop)
_Status: Queued — triggers after Phase 1 completion and Shael's input_

### Shael's Direction
_(Populated after Phase 1 completion)_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|

## Artifacts
- **Design Brief:** `snn_applied_finance/research/pipeline_builds/v4-analysis_design_brief.md`
- **Architect Design:** `snn_applied_finance/research/pipeline_builds/v4-analysis_architect_analysis_design.md`
- **Critic Review:** `snn_applied_finance/research/pipeline_builds/v4-analysis_critic_analysis_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/v4-analysis_state.json`
- **Notebook:** `snn_applied_finance/notebooks/crypto_v4_analysis.ipynb`
