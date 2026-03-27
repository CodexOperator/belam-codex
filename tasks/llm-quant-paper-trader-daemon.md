# Task: Live Paper Trading Daemon (15m Resolution)

**Scope:** Build and test a lightweight daemon that runs LightGBM trading signals against dYdX testnet in real-time, executing on every 15-minute candle close.

**Deliverables:**
1. `llm-quant-finance/backtesting/live/paper_trader.py` — Main daemon loop
2. `llm-quant-finance/backtesting/live/lgbm_signal_generator.py` — LightGBM signal wrapper
3. Integration test against real Binance data + dYdX testnet
4. README with deployment instructions

## Daemon Architecture

### Signal Pipeline (per 15m candle close)

```
[Binance 15m candle] → [Load & preprocess] → [LightGBM model] 
                                                    ↓
                              [Regime filter + gate] → [SignalType.LONG/SHORT/FLAT]
                                                    ↓
                              [Confidence scale size] → [dYdX market order]
                                                    ↓
                              [Log trade + update state]
```

### Core Components

**LgbmSignalGenerator class:**
- Wraps trained LightGBM model from `llm-quant-finance/microcap_swing/models/`
- Inputs: 15m candles from Binance (fetched live via `backtesting/data/`)
- Feature computation: reuse `microcap_swing/src/features.py` exactly (no copy, import)
- Regime detection: import `src/live_regime.py` for current state
- Confidence calibration: load from `llm-quant-finance/microcap_swing/data/results/` (from S5)
- Outputs: `SignalSeries` (implements `SignalGenerator` protocol)

**PaperTraderDaemon class:**
- Runs on 15-minute schedule (via cron or systemd timer, not polling)
- Fetches latest Binance 15m candle
- Generates signal via LgbmSignalGenerator
- Executes via DydxExecutor (from Task 1)
- Logs all signals, orders, P&L to JSONL file
- Handles graceful shutdown on SIGTERM

**Execution Logic:**
- Signal: LONG → Check open SHORT → close if any → open LONG ($25 notional)
- Signal: SHORT → Check open LONG → close if any → open SHORT ($25 notional)
- Signal: FLAT → close all positions, no new entry
- Position size = $25 × confidence (confidence in [0.3, 1.0], below 0.3 = FLAT)
- Stop-loss: 1.5x ATR below entry (long) / above entry (short), limit order

**Tokens:**
- BTC-USD, ETH-USD, SOL-USD (only majors available on dYdX)
- $25 notional per active position (total exposure ~$75 max)
- Total testnet USDC: $500 (from Task 1 setup)

### Key Design Decisions

**Why 15m, not 1m or 5m:**
- LightGBM trained on 15m candles (S3A best performance)
- Avoids high-frequency noise and tick-by-tick fill issues
- dYdX testnet orderbook has enough depth for $25 orders

**Why schedule-based, not streaming:**
- Simpler to reason about (one signal per candle close, not multiple per bar)
- Lower dYdX testnet load (1 order per token per 15m = ~12 orders/token/day)
- Deterministic behavior: same signal at same time always

**Confidence Scaling:**
- Model outputs confidence [0.3, 1.0] (from S5 calibration)
- Position size = $25 × min(1.0, confidence)
- Example: confidence 0.5 → $12.50 position

### Signature

```python
class LgbmSignalGenerator:
    """Generate signals from trained LightGBM model and live candles.
    
    Args:
        model_path: Path to trained model (pickle or joblib)
        symbols: ["BTC-USD", "ETH-USD", "SOL-USD"]
    """
    
    async def generate_signals(self, symbol: str) -> TradingSignal:
        """Fetch latest candles, compute features, run model, return signal.
        
        Returns:
            Single TradingSignal for the just-closed 15m candle
        """

class PaperTraderDaemon:
    """Live paper trading daemon (15m resolution).
    
    Args:
        signal_gen: LgbmSignalGenerator instance
        executor: DydxExecutor instance
        log_dir: Directory for trade logs
        symbols: List of symbols to trade
    
    Methods:
        async run_once() -> None: Fetch candles, generate signals, execute
        async run_daemon() -> None: Schedule run_once every 15 minutes
    """
    
    async def run_once(self) -> None
    async def run_daemon(self) -> None
    def _log_trade(self, symbol: str, signal: TradingSignal, order: Order) -> None
```

## Test Strategy

**Integration Test (Real Binance + dYdX Testnet):**
- [ ] Test 1: Instantiate LgbmSignalGenerator, load model
- [ ] Test 2: Generate signal for BTC (fetch live candles, compute features, run model)
- [ ] Test 3: Verify signal type is in {LONG, SHORT, FLAT}
- [ ] Test 4: Verify confidence is in [0.3, 1.0]
- [ ] Test 5: Run one full cycle: signal → dYdX order → log
- [ ] Test 6: Open long BTC, daemon runs next cycle, generates FLAT, closes position
- [ ] Test 7: Position sizing: confidence 0.6 → actual order $15 (0.6 × $25)
- [ ] Test 8: Multi-token: all three tokens trade, no cross-margin issues
- [ ] Test 9: Error handling: network timeout on candle fetch → skip signal, log error, retry next cycle
- [ ] Test 10: Graceful shutdown: SIGTERM → close all positions, sync logs, exit

**Real Data:**
- Live Binance API for 15m candles (via `backtesting/data/BinanceFetcher`)
- Real dYdX testnet for order execution
- Real LightGBM model from S3A

**No Mocks:**
- ❌ Do NOT mock Binance API or dYdX client
- ✅ Use real Binance public API (no auth needed for fetching candles)
- ✅ Real dYdX testnet (free USDC)

## Dependencies

**New:**
- `schedule >= 1.2.0` (for cron-like scheduling)
- `python-dotenv` (for env var loading, if not present)

**Existing (from Task 1):**
- `dydx-v4-client >= 1.0.0`
- `llm-quant-finance/backtesting/` modules (DydxExecutor, data fetchers)
- `llm-quant-finance/microcap_swing/` (trained model, features.py, live_regime.py)

## File Structure

```
llm-quant-finance/
├── backtesting/live/
│   ├── __init__.py
│   ├── paper_trader.py           (main daemon, ~300-400 lines)
│   ├── lgbm_signal_generator.py  (signal wrapper, ~150-200 lines)
│   ├── tests/
│   │   └── test_paper_trader.py  (10 integration tests, ~350 lines)
│   ├── logs/                      (auto-created, holds JSONL trade logs)
│   │   └── .gitkeep
│   └── TESTNET_ADDRESS.txt        (from Task 1, referenced here)
├── requirements-backtest.txt      (already has dydx-v4-client, add schedule)
└── microcap_swing/
    └── (existing: models/, src/features.py, src/live_regime.py, data/results/)
```

## Signal Flow Example

**Scenario:** Current time = 2026-03-27 08:00:00 UTC, just closed 15m candle.

1. **Fetch candles:** Get BTC/ETH/SOL 15m candles from Binance, last 100 bars
2. **Compute features:** `features.py` → 84-feature vectors
3. **Regime gate:** `live_regime.py` → current regime + confidence
4. **LightGBM predict:** model.predict(features[-1:]) → raw probability
5. **Confidence calibration:** S5 calibration curve → adjusted confidence
6. **Signal:** If probability > threshold → LONG/SHORT, else FLAT
7. **Size scaling:** Confidence × $25 → actual notional
8. **dYdX order:** Market buy/sell or close existing
9. **Log:** `logs/paper_trader_2026-03-27.jsonl` entry:
   ```json
   {
     "timestamp": "2026-03-27T08:00:00Z",
     "symbol": "BTC-USD",
     "signal": "LONG",
     "confidence": 0.72,
     "position_size_usd": 18.0,
     "order_id": "0x...",
     "fill_price": 43250.5,
     "status": "filled"
   }
   ```

## Acceptance Criteria

- [ ] All 10 integration tests pass
- [ ] Daemon runs 15m schedule without drift (cron or systemd timer)
- [ ] Signals use real Binance candles (not synthetic/old data)
- [ ] dYdX orders confirmed on real testnet
- [ ] Logs are valid JSONL, one entry per trade
- [ ] Error handling: network timeouts → log + retry (no crash)
- [ ] Graceful shutdown: SIGTERM closes all positions + syncs logs
- [ ] Type hints: full Pydantic models, mypy strict mode
- [ ] Code review: ruff linting passes

## Deployment (Manual, Testnet Only)

```bash
# 1. Install dependencies
cd llm-quant-finance
pip install -r requirements-backtest.txt
pip install schedule python-dotenv

# 2. Set env vars
export DYDX_MNEMONIC="<your testnet seed phrase>"
export BINANCE_API_KEY="<public key, not needed for public candles>"

# 3. Run once (test)
python -m backtesting.live.paper_trader --once

# 4. Run daemon (background)
nohup python -m backtesting.live.paper_trader > logs/daemon.log 2>&1 &
```

## Notes

- **Testnet-only phase:** This is paper trading on free testnet USDC. Not real money.
- **Next phase:** Mainnet with real capital (requires separate task, API key rotation, risk framework)
- **Monitoring:** Logs accumulate in `backtesting/live/logs/`; use daily rotation script if running long-term
- **Regime tracking:** `live_regime.py` already updated every run; this daemon just reads current state
- **Stop-loss logic:** Limit orders placed on dYdX; if trade moves against stop-loss before it fills, we're okay (position still open, will close on next signal)

## Related Tasks

- **Dependency:** Task 1 (dYdX Adapter) must complete first
- **Feeds into:** Future mainnet adapter (Task 3, if approved)
- **Uses:** Trained models from S3A (microcap_swing)
- **Uses:** Regime data from S10 (microcap_swing)
