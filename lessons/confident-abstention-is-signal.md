---
primitive: lesson
date: 2026-03-15
source: V3 Scheme B results
confidence: medium
project: snn-applied-finance
tags: [snn, trading, abstention]
applies_to: [snn-applied-finance]
---

# Confident Abstention Is a Real Signal Type

V3 Scheme B (delta→regression with HuberLoss δ=0.01) achieved the only positive net Sharpe (+0.45) by naturally learning to abstain — low prediction entropy (0.577 bits), turnover=0.36 meaning it only traded ~36% of opportunities.

The model bets infrequently but more accurately on those bets. HuberLoss incentivizes "say nothing" over "say something wrong."

**Caveat:** n=3 folds, t-stat≈0.48, p≈0.67 — NOT statistically significant. Needs 7+ folds to confirm. But the mechanism is sound and worth pursuing.
