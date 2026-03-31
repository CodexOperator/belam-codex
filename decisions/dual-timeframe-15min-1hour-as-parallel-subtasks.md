---
primitive: decision
status: accepted
created: 2026-03-26
author: shael
tags: [quant, swing-trading, timeframe]
related: [microcap-swing-signal-extraction]
promotion_status: exploratory
doctrine_richness: 2
contradicts: []
---

# Dual Timeframe (15-min / 1-hour) as Parallel Subtasks

## Decision
Run both 15-minute and 1-hour candle timeframes as separate subtasks (S3A and S3B) rather than committing to one upfront.

## Rationale
- Unknown which timeframe captures swing structure better for microcap tokens
- 15-min: more data points, finer granularity, noisier
- 1-hour: cleaner signals, fewer observations, may miss intra-hour moves
- Splitting into subtasks allows direct head-to-head comparison with identical feature/model pipeline
- Results from both feed into S11 synthesis for final timeframe recommendation

## Note
Both timeframes share the same feature engineering (S2) — multi-timeframe aggregation computes indicators at 5-min through daily regardless.
