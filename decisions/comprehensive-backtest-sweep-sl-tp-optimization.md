---
primitive: decision
date: 2026-03-31
status: active
rationale: >
  Rather than guessing stop-loss, take-profit, and trailing stop parameters from
  theory, run a professional backtest sweep across all trained models (all tokens ×
  all timeframes) to empirically determine optimal trade management parameters.
upstream: [confidence-gating-070-selectivity-over-coverage, quant-baseline-v2-multi-horizon-swing-target]
downstream: []
tags: [instance:main, quant, backtesting, lightgbm, microcap]
promotion_status: exploratory
doctrine_richness: 10
contradicts: []
---

# comprehensive-backtest-sweep-sl-tp-optimization

## Decision

Run a full backtest sweep across all LightGBM microcap swing models (all tokens × 15m, 1h, 4h timeframes) using VectorBT to empirically determine best stop-loss, take-profit (full + partial), trailing stop, and time-limit parameters, rather than using fixed heuristic values.

## Context

After observing that SOL showed nonlinear uplift at 80% confidence and ETH 15m had strong results, it became clear that trade management parameters (SL/TP/trailing/time limits) are at least as important as the signal threshold. Professional-grade results require optimizing both axes.

## Scope

- Tokens: BONK, WIF, TRUMP, PENGU, FARTCOIN, SOL, ETH, BTC
- Timeframes: 15m, 1h (and 4h/1d if data available)
- Confidence thresholds: 0.60, 0.70, 0.75, 0.80, 0.85, 0.90
- Parameters swept: stop-loss (0.5-5% ATR multiples), take-profit (1:1 to 1:4 R:R), partial TP, trailing stops, max hold candles
- Evaluation metrics: Sharpe, Calmar, win rate, max drawdown, profit factor, total return

## Rationale

Using VectorBT's parameter sweep capabilities avoids manual tuning bias and surfaces the true parameter sensitivity landscape. Confidence-weighted position sizing mode will also be compared against threshold-binary entry mode.
