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
| analysis_architect_design | 2026-03-17 | architect | Design complete — 6 sections, 17 visualizations, 6 statistical tests. Key finding: 97.8% dead network rate, all pkl data is exponential scheme only, pkl files are cumulative (must deduplicate to 96 records). Analysis is root-cause investigation, not performance ranking. |
| analysis_critic_review_blocked | 2026-03-17 | critic | BLOCKED: BLOCK-1: Effect sizes missing from all 6 tests (Cohen's d, odds ratio, rank-biserial r). FLAG-1: Post-hoc test labeling. FLAG-2: Per-experiment Bonferroni impossible at n=3 (df=2, t_crit≈14.1). FLAG-3: NaN handling gaps (variable trajectory lengths, degenerate confidence arrays, missing fields). FLAG-4: Random seed for PnL sampling. FLAG-5: Section 1.4 uses r_up<0.05 but dead threshold is 0.02. |
| analysis_architect_design | 2026-03-17 | architect | Design revised — BLOCK-1 resolved (effect sizes added to all 6 tests: Cohen's d, odds ratio, rank-biserial r); FLAG-1 (Type column added, post-hoc labeling explicit); FLAG-2 (per-experiment t-test replaced with descriptive ranked table); FLAG-3 (NaN handling: .get() defaults, trajectory padding spec, KDE guard for degenerate arrays); FLAG-4 (random_state=42); FLAG-5 (r_up range corrected to [0,0.02], output range [0.5,0.505], reference line specified) |
| analysis_critic_review | 2026-03-17 | critic | APPROVED. All 1 block + 5 flags resolved. Effect sizes added (Cohen's d, odds ratio, rank-biserial r). Post-hoc labeling added. Per-experiment Bonferroni replaced with descriptive table. NaN handling specified (padding, KDE guard, .get() defaults). Random seed added. Section 1.4 math corrected to dead threshold 0.02. |
| analysis_builder_implementation | 2026-03-17 | builder | crypto_v4_analysis.ipynb: 74 cells (29 code), 17 visualizations, 5 statistical tests. All ANALYSIS_AGENT_ROLES standards met. Dedup, KDE guard, dead threshold annotations, trajectory padding, Phase 2 placeholder. |

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
