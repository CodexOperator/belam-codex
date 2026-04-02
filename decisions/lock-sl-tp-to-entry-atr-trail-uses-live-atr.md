---
primitive: decision
status: accepted
date: 2026-04-02
context: V10 backtest uses VectorBT which snapshots stop levels at entry bar — live bridge was recalculating from current ATR each cycle
alternatives: [keep rolling ATR for all stops, use EWMA-smoothed ATR]
rationale: Backtest-live parity is critical — rolling ATR stops were an unintended divergence that changed the risk profile of the strategy
consequences: [SL/TP now fixed at entry, trailing stop still adapts to volatility, entry_atr persisted in bridge_state.json]
upstream: [decision/app-level-sl-trailing-stop-not-exchange-side, decision/comprehensive-backtest-sweep-sl-tp-optimization]
downstream: [decision/bridge-daemon-state-persistence-and-graceful-shutdown]
tags: [instance:main, quant, live-bridge, backtest-parity]
importance: 4
---

# Lock SL/TP to Entry ATR, Trail Uses Live ATR

Fixed `check_atr()` in `stop_loss.py` to lock SL and TP to `entry_atr` (captured at position open), matching V10 backtest behavior where VectorBT snapshots stop levels at entry. Only trailing stop uses `current_atr` so it adapts to live volatility.

The `entry_atr` is persisted to `bridge_state.json` and restored on daemon restart.
