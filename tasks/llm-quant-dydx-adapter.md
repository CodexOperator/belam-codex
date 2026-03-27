# Task: dYdX v4 Execution Adapter

**Scope:** Build and test a production-ready dYdX v4 adapter that converts LightGBM trading signals into live perpetual futures orders on dYdX testnet.

**Deliverables:**
1. `llm-quant-finance/backtesting/strategies/dydx_adapter.py` — dYdX v4 execution client
2. Integration tests against dYdX testnet (real network, free faucet USDC)
3. Documentation and example usage

## Adapter Design

### Core Components

**DydxExecutor class:**
- Wraps `dydx-v4-client` SDK (install from PyPI)
- Manages account state: balances, open positions, margin availability
- Implements order lifecycle: create → fill → track
- Handles position tracking (entry price, size, unrealized PnL)

**Order Management:**
- Market orders for entries (immediate fill at best available price)
- Limit orders for stop-losses (ATR-based, 1.5x ATR from entry)
- Position management: flatten existing, enter new, maintain hedges
- Trade size: confidence-scaled from [0,1] → [0.1x, 1.0x] position

**Risk Controls (hardcoded, no config):**
- Min order size: $1 notional
- Max position: $100 notional per token (prevents over-leverage)
- Stop-loss: 1.5x ATR below entry (long) / above entry (short)
- Slippage budget: 0.5% for market orders

**Account Management:**
- Auto-deposit $500 testnet USDC (from faucet, on-chain) before first trade
- Track margin usage, maintenance level
- Reject orders if margin ratio would drop below 2.0x (conservative)

### Signature

```python
class DydxExecutor:
    """Execute trading signals on dYdX v4 testnet.
    
    Args:
        mnemonic: BIP39 seed phrase (env var or passed)
        network: "testnet" or "mainnet" (default "testnet")
        tokens: List of (symbol, product_id) to trade, e.g. [("BTC", "BTC-USD"), ...]
    
    Attributes:
        account: Current account state (balance, margin, positions)
        positions: Dict[symbol -> Position] with entry price, size, pnl
    """
    
    async def market_order(self, symbol: str, side: "BUY"|"SELL", 
                          size_usd: float) -> Order
    async def limit_order(self, symbol: str, side: "BUY"|"SELL", 
                         price: float, size_usd: float) -> Order
    async def get_position(self, symbol: str) -> Position
    async def close_position(self, symbol: str) -> Order
    async def fetch_account_state(self) -> Account
```

## Test Strategy

**Real Testnet Tests (not mocked):**
- [ ] Test 1: Connect to testnet, fetch account state (no trading)
- [ ] Test 2: Place limit buy order for BTC at market price − 5% (should not fill immediately)
- [ ] Test 3: Place market sell order, verify fill within 100ms
- [ ] Test 4: Open long BTC position ($20 notional), verify position tracking
- [ ] Test 5: Open short ETH position ($20 notional), verify position tracking
- [ ] Test 6: Close long position with market order, verify zero position
- [ ] Test 7: Stop-loss trigger: open long, place stop-loss at 1.5x ATR below, verify cancel on normal close
- [ ] Test 8: Confidence scaling: place order with confidence 0.5, verify size is 0.5x

**Real Data:**
- Use live Binance candles (via `llm-quant-finance/backtesting/data/`) for ATR computation
- dYdX testnet balance retrieved from chain, not mocked
- All orders hit real dYdX testnet orderbook

**No Mocks:**
- ❌ Do NOT mock the dYdX client or network calls
- ✅ Use real dYdX testnet (it's free and fast)
- ✅ Real Binance candles for feature computation

## Dependencies

**New:**
- `dydx-v4-client >= 1.0.0` (add to `requirements-backtest.txt`)
- `python-bip39` (for mnemonic handling, if not already present)

**Existing:**
- `backtesting/` modules (base_adapter, vectorbt_adapter for reference)
- `backtesting/data/` for candle fetching
- `backtesting/costs/` models.py for slippage/impact

## Acceptance Criteria

- [ ] All 8 tests pass against dYdX testnet
- [ ] Adapter implements `SignalGenerator` protocol (for future integration with LightGBM)
- [ ] Documentation: docstrings + example script showing signal → order flow
- [ ] Error handling: graceful recovery from network timeouts, margin errors, insufficient balance
- [ ] Type hints: full Pydantic models for Order, Position, Account state
- [ ] Code review: passes linting (ruff, mypy strict mode)

## Context

**Why testnet-only for this phase:**
- Free USDC from faucet, no real capital at risk
- Fast settlement (1-2 sec), good for testing order lifecycle
- Identical API to mainnet, just different chain ID

**Next phase (Task 2):**
- LightGBM signal generator that feeds into DydxExecutor
- Daemon loop that runs every 15 minutes
- Live Telegram notifications on orders

## Files to Create

```
llm-quant-finance/backtesting/strategies/
├── dydx_adapter.py          (main implementation, ~300-400 lines)
├── dydx_types.py            (Pydantic models for Order, Position, Account)
└── tests/
    └── test_dydx_testnet.py (8 integration tests, ~250 lines)
```

## Notes

- Use `async/await` throughout (dydx-v4-client is async-first)
- Log all orders to `~/.openclaw/workspace/machinelearning/llm-quant-finance/backtesting/live/logs/dydx_orders.jsonl`
- Testnet address will be auto-generated from mnemonic; save it to `~/.openclaw/workspace/machinelearning/llm-quant-finance/backtesting/live/TESTNET_ADDRESS.txt` for reference
- Do NOT hardcode API keys; use env vars (`DYDX_MNEMONIC`)
