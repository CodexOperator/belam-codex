---
primitive: lesson
date: 2026-03-31
source: session main 2026-03-30
confidence: high
upstream: [confidence-gating-070-selectivity-over-coverage]
downstream: []
tags: [instance:main, quant, lightgbm, confidence, microcap]
promotion_status: promoted
doctrine_richness: 9
contradicts: []
---

# confidence-threshold-80pct-nonlinear-uplift

## Context

During the comprehensive backtest planning session, Shael noted that SOL showed "good uplift at 70% confidence" but "even better at 80%". ETH 15m model also showed strong results at 80% confidence threshold. This prompted a sweep of all models at all confidence thresholds.

## What Happened

Observed that stepping the confidence threshold from 70% → 80% yields nonlinear improvement in signal quality for SOL and ETH microcap/major models. The 70% threshold already demonstrated selectivity gains over no filtering, but 80% provided additional lift beyond what the linear extrapolation would predict.

## Lesson

Confidence thresholds above 0.70 can yield nonlinear uplift — the improvement from 70%→80% is often greater than from 60%→70%, making it worth sweeping the full range rather than stopping at the first working threshold.

## Application

When calibrating confidence gates for trading signals, always sweep at least 0.60, 0.70, 0.75, 0.80, 0.85, 0.90. Don't assume linear degradation in trade count justifies stopping at 0.70. Test all tokens and timeframes independently as the nonlinearity varies by asset.
