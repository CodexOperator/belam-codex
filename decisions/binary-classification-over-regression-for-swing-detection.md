---
primitive: decision
status: accepted
created: 2026-03-26
author: shael+belam
tags: [quant, ml, swing-trading, classification]
related: [microcap-swing-signal-extraction, quant-microcap-crypto-baseline]
promotion_status: exploratory
doctrine_richness: 8
contradicts: []
---

# Binary Classification Over Regression for Swing Detection

## Decision
Predict swing existence ("Will return exceed ATR-based threshold T% over next N candles?") rather than predicting price or return magnitude.

## Rationale
- Price prediction is noisy and rewards overfitting to magnitude
- Swing existence is a cleaner binary signal that maps directly to a trading decision
- ATR-dynamic thresholds adapt to each token's volatility regime (no fixed % that becomes stale)
- MFE-based labeling captures "was this tradeable?" rather than "what was the close-to-close return?"
- Confidence gating (P ≥ 0.70) makes selectivity the primary lever, not accuracy

## Context
The `quant-microcap-crypto-baseline` task uses regression. This decision applies to the parallel `microcap-swing-signal-extraction` track. Both run simultaneously — regression results inform classification feature selection.

## Tradeoffs
- Lose granularity of return magnitude (addressed by combining with ATR-based take-profit levels)
- Label construction is more complex (MFE computation over prediction horizon)
- Threshold T% choice matters — mitigated by making it ATR-dynamic rather than fixed
