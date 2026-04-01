---
primitive: task
title: Git-diff handoff context for pipeline stage transitions
status: open
priority: high
tags: [pipelines, orchestration, handoff, git, context]
pipeline: git-diff-handoff-context
upstream: []
downstream: []
created: "quant,microcap-swing,feature-engineering"
pipeline_template: ""
current_stage: null
pipeline_status: ""
launch_mode: queued
---

## Higher Timeframe Feature Generation: 12h, 1d, 1w, 1M

### Goal
Extend the MTF feature pipeline to generate 12-hour, daily, weekly, and monthly resolution features for BTC, ETH, SOL. These are REQUIRED for 4h+ model timeframes to function.

### Problem
Current MTF config: [5m, 15m, 1h, 4h, 1d]. The 4h model collapses to majority-class prediction because its highest TF anchor (1d) has insufficient resolution. The fractal hierarchy requires each model to have features from 2-4x higher timeframes.

### What's Needed
| Base Model TF | Needs MTF Features From |
|---|---|
| 4h | 12h, 1d, 1w |
| 12h | 1d, 1w, 1M |
| 1d | 1w, 1M |

### Implementation Plan
1. Add resampling support: 12h, 1w, 1M to data_pipeline.py (1d already exists)
2. Update FeatureConfig.mtf_timeframes to include new intervals
3. Compute RSI-14, MACD, ROC-10, OBV at each new timeframe
4. Generate and save parquet files for BTC, ETH, SOL at all new timeframes
5. Validate: feature count, NaN rates, alignment with base TF timestamps
6. Run quick LGBM test at 4h with new features to confirm the model learns

### Additional Features for Higher TFs
- Weekly RSI, monthly RSI (macro momentum anchors)
- Daily ADX (trend strength at daily scale)
- Weekly Bollinger bandwidth (macro volatility)
- Funding rate dynamics (unique to crypto, daily resolution)
- Open interest changes (daily)

### Tokens
- BTC, ETH, SOL (majors with sufficient history)

### Success Criteria
- 4h LGBM shows >0% lift over majority baseline (currently 0.00%)
- Daily LGBM achieves positive lift with weekly/monthly features
- No NaN explosion from sparse higher-TF data
