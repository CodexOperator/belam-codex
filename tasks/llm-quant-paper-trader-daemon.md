# Task: Live Paper Trading Daemon (15m Resolution)

**Dependency:** Task `llm-quant-dydx-adapter` must be complete first. `DydxExecutor` and `dydx_types.py` must exist at `backtesting/strategies/`.

**Scope:** Build the signal generation layer (LightGBM → regime filter → signal) and a 15-minute daemon that executes those signals via `DydxExecutor` on dYdX testnet.

**Working directory:** `/home/ubuntu/.hermes/workspace/machinelearning/llm-quant-finance/`
**Python venv:** `.venv/` — activate before running anything

---

## Critical context: Model is NOT serialized

The LightGBM model from S3A **was not saved to disk** — `model_lightgbm.py` saves predictions and metrics, not model artifacts. The `LgbmSignalGenerator` must therefore:

1. **Re-train the model on startup** using walk-forward on existing cached data, OR
2. **Add model serialization** to `model_lightgbm.py` first, then load the saved model

**Recommended approach (Option 2):** Add a `--save-model` flag to `model_lightgbm.py` that saves the final fold's booster as `data/models/{token}_{timeframe}_final.lgb`. Then call it once during setup to produce the model files, and load them in `LgbmSignalGenerator`.

The full-history data is already cached at:
- `../microcap_swing/data/features_500d_baseline/{token}/{token}_15m.parquet` (500-day baseline)
- Full history parquets may need re-fetching via `src/data_pipeline.py`

---

## Deliverables

1. **`microcap_swing/src/model_lightgbm.py`** — add `--save-model` flag + `save_model()` function
2. **`backtesting/live/lgbm_signal_generator.py`** — `LgbmSignalGenerator` class
3. **`backtesting/live/paper_trader.py`** — `PaperTraderDaemon` class + CLI entrypoint
4. **`backtesting/live/tests/test_paper_trader.py`** — 9 integration tests
5. **`backtesting/live/README.md`** — deployment instructions

---

## Step 0: Add model serialization and generate model files

First, modify `microcap_swing/src/model_lightgbm.py`:

```python
# Add to save_results():
import lightgbm as lgb

def save_results(token, timeframe, results, report):
    # ... existing code ...

    # NEW: Save final fold booster
    if results.get("final_booster") is not None:
        models_dir = PROJECT_ROOT / "data" / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        model_path = models_dir / f"{token.lower()}_{timeframe}_final.lgb"
        results["final_booster"].save_model(str(model_path))
        paths["model"] = model_path
        log.info(f"Saved model to {model_path}")
```

Also ensure the last fold's booster is added to the results dict as `"final_booster"`.

Then run for BTC, ETH, SOL using the 500d baseline data:
```bash
cd /home/ubuntu/.hermes/workspace/machinelearning/llm-quant-finance
source .venv/bin/activate
cd microcap_swing
python -m src.model_lightgbm --token BTC --timeframe 15m
python -m src.model_lightgbm --token ETH --timeframe 15m
python -m src.model_lightgbm --token SOL --timeframe 15m
```

Verify model files exist:
```
microcap_swing/data/models/btc_15m_final.lgb
microcap_swing/data/models/eth_15m_final.lgb
microcap_swing/data/models/sol_15m_final.lgb
```

---

## LgbmSignalGenerator Design

```python
# backtesting/live/lgbm_signal_generator.py

class LgbmSignalGenerator:
    """Generate trading signals from trained LightGBM model + live Binance candles.

    Imports (do not copy):
      - microcap_swing.src.features for feature engineering
      - microcap_swing.src.live_regime for regime state
        (live_regime.py is at: ../microcap_swing/src/live_regime.py)
      - backtesting.data.binance_fetcher for live candles

    Args:
        model_dir: Path to directory with *.lgb model files
                   Default: Path("../microcap_swing/data/models")
        symbols: ["BTC-USD", "ETH-USD", "SOL-USD"]
        confidence_threshold: Below this, emit FLAT (default 0.30)

    Usage:
        gen = LgbmSignalGenerator()
        signal = await gen.generate_signal("BTC-USD")
        # signal.signal: SignalType.LONG / SHORT / FLAT
        # signal.confidence: float in [0, 1]
    """

    def __init__(self, model_dir: Path = None, symbols: list[str] = None,
                 confidence_threshold: float = 0.30):
        ...

    async def generate_signal(self, symbol: str) -> TradingSignal:
        """
        1. Fetch last 200 bars of 15m candles from Binance public API
           symbol mapping: "BTC-USD" → "BTCUSDT"
        2. Compute features using microcap_swing.src.features.compute_features()
        3. Get regime state via microcap_swing.src.live_regime.get_regime(symbol)
        4. Run LightGBM model on last row of features
        5. Convert multiclass probabilities to SignalType:
           - class 2 (up) probability > threshold → LONG
           - class 0 (down) probability > threshold → SHORT
           - else → FLAT
        6. Confidence = max(p_up, p_down) if not FLAT, else 0.0
        7. If regime is "bear" and signal is LONG → downgrade to FLAT
           (don't fight the regime)
        8. Return TradingSignal(timestamp, signal, confidence)
        """
```

**Symbol mapping** (Binance vs dYdX):
- `"BTC-USD"` → Binance: `"BTCUSDT"`, dYdX: `"BTC-USD"`
- `"ETH-USD"` → Binance: `"ETHUSDT"`, dYdX: `"ETH-USD"`
- `"SOL-USD"` → Binance: `"SOLUSDT"`, dYdX: `"SOL-USD"`

**Feature computation:** Import from `microcap_swing.src.features` (the module is in `../microcap_swing/src/features.py` relative to `llm-quant-finance/`). Add `microcap_swing/` to sys.path or use importlib if needed.

**Live regime:** `microcap_swing/src/live_regime.py` — use its one-shot mode or call `get_regime_state(symbol)` if that function exists. Check the file to find the right entry point.

---

## PaperTraderDaemon Design

```python
# backtesting/live/paper_trader.py

class PaperTraderDaemon:
    """15-minute paper trading daemon.

    Runs run_once() every 15 minutes. On each cycle:
    1. For each symbol: generate signal
    2. Compare to current position
    3. Execute via DydxExecutor if action needed
    4. Log result

    Args:
        signal_gen: LgbmSignalGenerator
        executor: DydxExecutor (already connected)
        symbols: ["BTC-USD", "ETH-USD", "SOL-USD"]
        position_size_usd: Base position size (default $25)
        log_dir: Where to write JSONL trade logs
    """

    async def run_once(self) -> list[dict]:
        """Run one full cycle across all symbols. Returns list of trade log entries."""

    async def run_daemon(self) -> None:
        """Run run_once() every 15 minutes. Handles SIGTERM gracefully."""

    def _log_trade(self, entry: dict) -> None:
        """Append to logs/paper_trader_YYYY-MM-DD.jsonl"""
```

**Execution logic per symbol:**
```
current_pos = await executor.get_position(symbol)
signal = await signal_gen.generate_signal(symbol)
size = position_size_usd * signal.confidence

if signal.signal == LONG:
    if current_pos and current_pos.side == "SHORT":
        await executor.close_position(symbol)
    if not current_pos or current_pos.side != "LONG":
        await executor.market_order(symbol, "BUY", size)

elif signal.signal == SHORT:
    if current_pos and current_pos.side == "LONG":
        await executor.close_position(symbol)
    if not current_pos or current_pos.side != "SHORT":
        await executor.market_order(symbol, "SELL", size)

elif signal.signal == FLAT:
    if current_pos:
        await executor.close_position(symbol)
```

**CLI entrypoint:**
```bash
# Run once (for testing)
python -m backtesting.live.paper_trader --once

# Run daemon
python -m backtesting.live.paper_trader --daemon
```

**SIGTERM handling:** On SIGTERM, finish current cycle, close all positions, write final log entry, exit cleanly.

---

## Integration Tests

Tests live in `backtesting/live/tests/test_paper_trader.py`.

**Setup** (run once before tests):
```bash
export DYDX_MNEMONIC=$(cat backtesting/live/TESTNET_MNEMONIC.txt)
```

**Test list:**
1. `test_model_files_exist` — verify btc/eth/sol `.lgb` files are present in `microcap_swing/data/models/`
2. `test_signal_generator_loads` — instantiate `LgbmSignalGenerator`, verify models load without error
3. `test_generate_signal_btc` — call `generate_signal("BTC-USD")`, verify returns `TradingSignal` with signal in {LONG, SHORT, FLAT}
4. `test_generate_signal_confidence` — verify confidence is float in [0.0, 1.0]
5. `test_generate_all_symbols` — generate signals for all 3 symbols, all return valid TradingSignal
6. `test_run_once_full_cycle` — instantiate daemon with real executor, call `run_once()`, verify log entries written for all 3 symbols
7. `test_position_sizing` — mock signal with confidence=0.6, verify actual order size = 0.6 × $25 = $15
8. `test_flat_closes_position` — open $15 BTC long, then call `run_once()` with signal patched to FLAT, verify position closed
9. `test_log_format` — after `run_once()`, read JSONL log, verify entries have: timestamp, symbol, signal, confidence, position_size_usd, status

**Note on Test 6:** Do NOT wait for two 15-minute cycles. Call `run_once()` directly — it's a synchronous-ish call that runs one full cycle. The daemon schedule is separate from the per-cycle logic.

**Note on Test 8:** Patch the signal generator to return FLAT using `unittest.mock.patch` on `generate_signal`. The executor calls are still real testnet.

---

## Acceptance Criteria

- [ ] Model files generated and present for BTC, ETH, SOL
- [ ] All 9 tests pass
- [ ] `run_once()` completes within 30s (signal gen + 3 orders)
- [ ] JSONL logs written with correct schema per trade
- [ ] SIGTERM handler closes positions cleanly
- [ ] `ruff check` passes
- [ ] README documents: setup, env vars, run commands, log format

---

## README Template

````markdown
# Live Paper Trader

Trades BTC-USD, ETH-USD, SOL-USD on dYdX v4 testnet using LightGBM signals.

## Setup

```bash
cd llm-quant-finance
source .venv/bin/activate
pip install -r requirements-backtest.txt
export DYDX_MNEMONIC="<your 24-word seed phrase>"
```

## First Run

```bash
# Generate testnet wallet (one-time)
python -m backtesting.live.setup_testnet

# Run one cycle (test)
python -m backtesting.live.paper_trader --once

# Run daemon (background, 15m cycles)
nohup python -m backtesting.live.paper_trader --daemon > backtesting/live/logs/daemon.log 2>&1 &
```

## Log Format

Logs are written to `backtesting/live/logs/paper_trader_YYYY-MM-DD.jsonl`:
```json
{"timestamp": "...", "symbol": "BTC-USD", "signal": "LONG",
 "confidence": 0.72, "position_size_usd": 18.0,
 "order_id": "...", "fill_price": 84250.0, "status": "FILLED"}
```
````

---

## Files to Create / Modify

```
llm-quant-finance/
├── microcap_swing/
│   ├── src/
│   │   └── model_lightgbm.py          MODIFY: add final_booster to results + save_model()
│   └── data/
│       └── models/                     CREATE (auto by script)
│           ├── btc_15m_final.lgb
│           ├── eth_15m_final.lgb
│           └── sol_15m_final.lgb
└── backtesting/
    └── live/
        ├── lgbm_signal_generator.py    CREATE
        ├── paper_trader.py             CREATE
        ├── README.md                   CREATE
        └── tests/
            └── test_paper_trader.py   CREATE
```
