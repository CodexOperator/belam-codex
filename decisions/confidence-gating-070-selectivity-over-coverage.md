---
primitive: decision
status: accepted
created: 2026-03-26
author: shael+belam
tags: [quant, risk-management, swing-trading]
related: [microcap-swing-signal-extraction, binary-classification-over-regression-for-swing-detection]
promotion_status: exploratory
doctrine_richness: 4
contradicts: []
---

# Confidence Gating at 0.70 — Selectivity Over Coverage

## Decision
Only trade when model confidence P(swing) ≥ 0.70. Accept trading only 10–20% of observations.

## Rationale
- At $5–10 trade sizes, opportunity cost of missing trades is negligible
- False positives cost real money (even small amounts compound); false negatives cost nothing
- Calibration requirement: 70% confidence must mean ~70% actual accuracy (reliability diagram verified)
- Selectivity dominates accuracy in low-capital research phase
- Threshold optimized post-hoc via precision-recall curve: maximize (precision × avg_profit) - (miss_rate × opportunity_cost)

## Additional Rules
- During Extreme Greed (F&G > 80): tighten to 0.80+
- Focal loss outputs are NOT calibrated — mandatory Platt/isotonic post-hoc before gating
