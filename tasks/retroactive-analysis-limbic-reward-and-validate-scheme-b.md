---
primitive: task
status: open
priority: medium
tags: [analysis, snn, research]
project: snn-applied-finance
created: 2026-03-24
depends_on: []
pipeline_template: 
current_stage: 
pipeline_status: 
launch_mode: queued
---
# Retroactive Analysis: Limbic-Reward & Validate-Scheme-B Pipelines

## Description
Both pipelines were archived on 2026-03-24 with completed experiment results but without formal analysis pipeline processing. Run deep analysis on both using analysis pipelines.

## Context
- Both pipelines experienced race conditions during orchestration that corrupted their state files
- Experiments ran successfully and results exist in `local_results/`
- Analysis reports exist (generated during local runs) but were never formally processed through the analysis pipeline

## Artifacts
### Limbic-Reward-SNN
- Results: `machinelearning/snn_applied_finance/notebooks/local_results/limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network/`
- Analysis report: `limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network_analysis_report.md`
- Notebook: `crypto_limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network_predictor.ipynb`

### Validate-Scheme-B
- Results: `machinelearning/snn_applied_finance/notebooks/local_results/validate-scheme-b/`
- Analysis report: `validate-scheme-b_analysis_report.md` + `validate-scheme-b_report.pdf`
- Followup analysis: `followup_analysis/` (critic followup, structured results)
- Notebook: `crypto_validate-scheme-b_predictor.ipynb`

## Action
Launch analysis pipelines for both when capacity is available. Extract lessons, update TECHNIQUES_TRACKER, and feed findings into future version planning.
