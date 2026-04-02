---
primitive: lesson
date: 2026-04-02
source: main session — bridge stop_loss.py audit
confidence: high
upstream: []
downstream: [decision/app-level-sl-trailing-stop-not-exchange-side, decision/comprehensive-backtest-sweep-sl-tp-optimization]
tags: [instance:main, quant, live-bridge, backtest-parity]
importance: 4
---

# Live Bridge ATR SL/TP Drift vs Backtest Fixed-at-Entry

Live bridge `check_atr()` was overwriting `track.entry_atr = current_atr` every cycle, causing SL and TP prices to drift with volatility. VectorBT backtest locks `sl_stop`/`tp_stop` at the entry bar's ATR fraction — stops are fixed for the life of the trade.

This mismatch meant live trading had tighter stops during low-vol periods and wider stops during high-vol, diverging from backtested behavior.

**Fix:** Use `entry_atr` (locked at registration) for SL/TP computation; only trailing stop uses live `current_atr`.
