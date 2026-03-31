---
primitive: lesson
date: 2026-03-31
source: session main 2026-03-30
confidence: high
upstream: []
downstream: []
tags: [instance:main, quant, backtesting, vectorbt, confidence]
promotion_status: candidate
doctrine_richness: 8
contradicts: []
---

# vectorbt-confidence-position-sizing-pattern

## Context

During the comprehensive backtest planning session, the team reviewed the VectorBT adapter code. The adapter supports two position sizing modes: "fixed" (all-in) and "confidence" (scale by signal confidence via size_type="value").

## What Happened

The `vectorbt_adapter.py` already implements confidence-scaled position sizing as a first-class mode. The "confidence" mode uses the signal's confidence score [0,1] directly to scale position size, delegating the sizing decision to the engine adapter rather than the signal generator.

## Lesson

VectorBT's confidence-weighted position sizing (confidence score × capital) is a cleaner architecture than threshold-based binary filtering — it naturally lets high-confidence signals take larger positions without needing manual threshold tuning.

## Application

Prefer confidence-weighted sizing mode when running VectorBT backtests on calibrated probability models. Reserve threshold-based filtering for generating clean signal series comparisons across confidence levels. The two approaches complement each other: sweep thresholds to understand the distribution, then use continuous confidence weighting in production.
