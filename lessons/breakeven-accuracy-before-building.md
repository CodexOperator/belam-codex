---
primitive: lesson
date: 2026-03-15
source: V2 transaction cost analysis + Production Quant Handbook
confidence: high
project: snn-applied-finance
tags: [trading, costs, validation]
applies_to: [snn-applied-finance]
promotion_status: exploratory
doctrine_richness: 0
contradicts: []
---

# Calculate Breakeven Accuracy Before Building

At 4h BTC with 0.3% avg |move| and 0.1% cost/trade, breakeven accuracy is ~67%. V2's 54% generates +0.024% gross edge per trade vs -0.1% cost. The model was doomed before it ran.

Paths to positive Sharpe:
- Confidence thresholding (trade top-30% signals only)
- Daily resolution (breakeven drops to ~55.1%)
- Maker orders (0.02% cost → breakeven ~50.7%)

Always calculate the minimum accuracy required for profitability at your target resolution and cost structure BEFORE committing to a model architecture.
