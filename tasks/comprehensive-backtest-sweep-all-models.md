---
primitive: task
status: open
priority: high
created: 2026-03-30
owner: belam
depends_on: []
upstream: [t13]
downstream: []
tags: [quant, backtest, lightgbm, microcap, majors, vectorbt]
pipeline_template: 
current_stage: 
pipeline_status: 
launch_mode: queued
---
# comprehensive-backtest-sweep-all-models

## Description

Run a professional-grade backtest optimization sweep across ALL microcap swing models
for all majors (BTC, ETH, SOL) and microcaps at all available candle periods. The goal
is to determine optimal risk parameters (stop loss, take profit, partial TP, trailing
stops, time limits) per model × token × timeframe × confidence gate.

Key observations driving this:
- SOL had good uplift at 70% confidence, even better at 80%
- ETH 15min model showed strong results at 80% confidence
- Need systematic comparison across the full grid to find best configs

## Phases

### Phase 1: Data & Model Pipeline
1. Fetch fresh OHLCV for all tokens × timeframes (15m, 1h, 4h, 1d)
2. Train LightGBM models for each token × timeframe via walk-forward pipeline
3. Save raw predictions with full confidence probability vectors

### Phase 2: Signal Bridge
4. Build LightGBM → SignalSeries adapter (model output → backtesting module format)
5. Implement confidence threshold sweep: 0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90

### Phase 3: Risk Parameter Optimization
6. Parameter sweep grid:
   - Stop loss: 0.5×, 1×, 1.5×, 2× ATR
   - Take profit (full exit): 1×, 1.5×, 2×, 3× ATR
   - Partial TP: 50% position at 1× ATR, remainder trails
   - Trailing stop: 0.5×, 1×, 1.5× ATR (activated after partial TP)
   - Time limit: 6h, 12h, 24h, 48h (forced exit if max bars exceeded)
7. Run sweep: all combos per token × timeframe × confidence gate

### Phase 4: Analysis & Selection
8. Aggregate results — rank by Sharpe, Sortino, profit factor, max drawdown
9. Deflated Sharpe Ratio (DSR) — control for multiple testing bias
10. Regime stability check — does best config hold across bull/bear/chop?
11. Final report — top 3-5 configs per token with equity curves

## Tokens
- **Majors (control):** BTC/USDT, ETH/USDT, SOL/USDT
- **Microcaps:** BONK, WIF, TRUMP, PENGU, FARTCOIN
- *Timeframes:* 15m, 1h (existing), + 4h, 1d (extend)

## Acceptance Criteria

- [ ] All token × timeframe models trained with walk-forward validation
- [ ] LightGBM → SignalSeries bridge working with confidence gating
- [ ] Full parameter sweep grid executed
- [ ] DSR applied to control for multiple testing
- [ ] Regime stability analysis across market conditions
- [ ] Summary report: top configs per token with equity curves
- [ ] End-to-end script: fetch → train → predict → sweep → report

## Infrastructure
- Models: `microcap_swing/src/model_lightgbm.py` (15m), `model_lightgbm_1h.py` (1h)
- Backtesting: `backtesting/strategies/vectorbt_adapter.py`
- Walk-forward: `backtesting/validation/walk_forward.py`
- Analysis: `backtesting/validation/analysis.py`
- Data: `backtesting/data/binance_fetcher.py`

## Notes

- Need to add ATR-based SL/TP/trailing to VectorBTAdapter (currently only does entry/exit signals)
- Partial take-profit requires custom VectorBT signal_func_nb or two-pass approach
- Consider VectorBT's built-in param optimization for GPU-accelerated sweep
- Total combos estimate: ~8 tokens × 4 timeframes × 7 confidence gates × ~96 risk combos = ~21,504 backtests
