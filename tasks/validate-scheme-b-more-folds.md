---
primitive: task
status: archived
priority: high
owner: builder
tags: [validation, statistics, snn]
pipeline: validate-scheme-b
project: snn-applied-finance
estimate: 4h
depends_on: []
version_label: v5-validation
pipeline_template: 
current_stage: 
pipeline_status: in_pipeline
launch_mode: queued
---
# Validate Scheme B Sharpe with 7+ Folds

V3 Scheme B (+0.45 Sharpe via abstention) is the only positive net Sharpe result but has n=3, t-stat≈0.48, p≈0.67 — NOT significant. Rerun with 7+ walk-forward folds to get proper statistical power.

## Steps
1. Extend walk-forward to 7-10 folds (expanding window)
2. Maintain 60-candle purge gap
3. Compute DSR (Deflated Sharpe Ratio) correcting for multiple testing
4. Compute PBO — must be < 0.5
5. Bootstrap CI for the abstention mechanism

## References
- [[confident-abstention-is-signal]]
- [[breakeven-accuracy-before-building]]
- quant-workflow skill → statistical hygiene section
