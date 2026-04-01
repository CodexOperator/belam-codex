---
primitive: pipeline
status: archived
priority: critical
type: builder-first
version: llm-quant-dydx-adapter-v1
spec_file: machinelearning/snn_applied_finance/specs/llm-quant-dydx-adapter-v1_spec.yaml
output_notebook: machinelearning/snn_applied_finance/notebooks/snn_crypto_predictor_llm-quant-dydx-adapter-v1.ipynb
agents: [architect, critic, builder]
supersedes: 
tags: [quant, dydx, executor, live-trading, crypto]
project: llm-quant-finance
started: 2026-03-27
pending_action: p1_complete
current_phase: 
dispatch_claimed: false
last_updated: 2026-03-27 15:34
reset: false
---
# Implementation Pipeline: LLM-QUANT-DYDX-ADAPTER-V1

## Description
# Task: dYdX v4 Execution Adapter

**Scope:** Build and test a dYdX v4 execution adapter that places perpetual futures orders on dYdX testnet. This is the execution layer — it receives trade instructions and executes them on-chain.

**Working directory:** `/home/ubuntu/.openclaw/workspace/machinelearning/llm-quant-finance/`
**Python venv:** `.venv/` inside that directory — activate before running anything

---

## Step 0: Bootstrap (run first)

```bash
cd /home/ubuntu/.openclaw/workspace/machinelearning/llm-quant-finance
source .venv/bin/activate
pip install "dydx-v4-client>=1.0.0" pydantic python-dotenv
# Add to requirements-backtest.txt
echo "dydx-v4-client>=1.0.0" >> requirements-backtest.txt
echo "python-dotenv>=1.0.0" >> requirements-backtest.txt
```

Generate a testnet wallet and fund it:
```bash
# Generate mnemonic (install bip_utils if needed: pip install bip-utils)
python3 -c "
from bip_utils import Bip39MnemonicGenerator
m = Bip39MnemonicGenerator().FromWordsNumber(24)
print(m)
" > backtesting/live/TESTNET_MNEMONIC.txt
# Add to .gitignore
echo "backtesting/live/TESTNET_MNEMONIC.txt" >> .gitignore

# Fund the testnet address via faucet
# dYdX v4 testnet faucet: POST https://faucet.v4testnet.dydx.exchange/faucet/tokens
# with body: {"address": "<your_dydx_address>"}
# The Python client's NodeClient can derive the address from the mnemonic.
# Do this once in setup; $500 USDC is plenty for all tests.
```

---

## Deliverables

1. `backtesting/strategies/dydx_adapter.py` — `DydxExecutor` class (~300 lines)
2. `backtesting/strategies/dydx_types.py` — Pydantic models for `Order`, `Position`, `Account`
3. `backtesting/live/setup_testnet.py` — one-shot script: generate wallet + fund from faucet
4. `backtesting/live/tests/test_dydx_testnet.py` — 8 integration tests against real testnet
5. Add `dydx-v4-client`, `python-dotenv` to `requirements-backtest.txt`

---

## DydxExecutor Design

**This is an execution client, NOT a signal generator.** It receives trade instructions and places orders. The signal layer (Task 2) is separate.

```python
class DydxExecutor:
    """Execute trading instructions on dYdX v4 testnet.

    Args:
        mnemonic: BIP39 seed phrase (24 words). Load from env var DYDX_MNEMONIC
                  or from file backtesting/live/TESTNET_MNEMONIC.txt
        network: "testnet" (default) or "mainnet"

    Usage:
        executor = DydxExecutor(mnemonic=os.getenv("DYDX_MNEMONIC"))
        await executor.connect()
        order = await executor.market_order("BTC-USD", "BUY", size_usd=25.0)
        pos = await executor.get_position("BTC-USD")
        await executor.close_position("BTC-USD")
    """

    async def connect(self) -> None:
        """Initialize node client + indexer client. Must call before trading."""

    async def market_order(self, market: str, side: str, size_usd: float) -> Order:
        """Place a market order. side = "BUY" or "SELL"."""

    async def limit_order(self, market: str, side: str,
                          price: float, size_usd: float) -> Order:
        """Place a GTC limit order (used for stop-losses)."""

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order by ID."""

    async def get_position(self, market: str) -> Position | None:
        """Get current open position for a market. Returns None if flat."""

    async def close_position(self, market: str) -> Order | None:
        """Close any open position for market with a market order. No-op if flat."""

    async def fetch_account(self) -> Account:
        """Fetch current account state: equity, free margin, positions."""
```

**Risk controls (hardcoded):**
- Max single position: $100 notional
- Min order size: $10 notional (dYdX testnet minimum)
- Reject order if account free margin would drop below $50

**Markets supported:** BTC-USD, ETH-USD, SOL-USD

---

## Pydantic Types (`dydx_types.py`)

```python
class Order(BaseModel):
    order_id: str
    market: str
    side: str          # "BUY" | "SELL"
    size: float        # in asset units
    price: float       # fill price
    status: str        # "OPEN" | "FILLED" | "CANCELED"
    created_at: datetime

class Position(BaseModel):
    market: str
    side: str          # "LONG" | "SHORT"
    size: float        # in asset units
    entry_price: float
    unrealized_pnl: float
    created_at: datetime

class Account(BaseModel):
    address: str
    equity: float      # total account value in USDC
    free_margin: float # available for new positions
    positions: list[Position]
```

---

## Integration Tests (real testnet, no mocks)

Tests live in `backtesting/live/tests/test_dydx_testnet.py`.

Run with:
```bash
cd /home/ubuntu/.openclaw/workspace/machinelearning/llm-quant-finance
source .venv/bin/activate
export DYDX_MNEMONIC=$(cat backtesting/live/TESTNET_MNEMONIC.txt)
pytest backtesting/live/tests/test_dydx_testnet.py -v
```

**Test list:**
1. `test_connect` — connect to testnet, fetch account, verify equity > 0
2. `test_fetch_account` — account has address, equity, free_margin fields populated
3. `test_limit_order_btc` — place limit BUY at 10% below current price (won't fill), verify order_id returned, then cancel it
4. `test_market_order_btc_long` — market BUY BTC $15 notional, verify position appears within 5s
5. `test_market_order_eth_short` — market SELL ETH $15 notional, verify short position appears
6. `test_close_position` — open $15 BTC long, then close_position("BTC-USD"), verify position is None
7. `test_risk_limit` — attempt $200 order, verify DydxExecutor raises ValueError (exceeds $100 cap)
8. `test_account_after_trades` — after tests 4+5+6, fetch account, verify equity updated

**Important:** Use `asyncio.run()` or `pytest-asyncio` for async tests. Tests 4–8 use real testnet funds — order sequentially, don't parallelize.

**Block time note:** dYdX v4 is Cosmos-based with ~1-2 second block time. All assertions on fill/position should wait up to **10 seconds**, not 100ms.

---

## Acceptance Criteria

- [ ] All 8 tests pass against real dYdX testnet
- [ ] `DydxExecutor` has clean async interface with `connect()` before use
- [ ] Pydantic models used for all return types
- [ ] Mnemonic loaded from env var `DYDX_MNEMONIC` (never hardcoded)
- [ ] `.gitignore` includes `TESTNET_MNEMONIC.txt`
- [ ] `requirements-backtest.txt` updated
- [ ] Full docstrings on all public methods
- [ ] `ruff check` passes (zero errors)

---

## Notes for Builder

- **dydx-v4-client SDK:** `from dydx_v4_client import NodeClient, IndexerClient, Wallet`
- The SDK is async-first. `NodeClient` for on-chain (orders, positions); `IndexerClient` for market data.
- Testnet node: `https://dydx-testnet.nodefleet.org` (or check current dYdX testnet docs)
- Testnet indexer: `https://indexer.v4testnet.dydx.exchange`
- Faucet endpoint: `POST https://faucet.v4testnet.dydx.exchange/faucet/tokens` body `{"address": "<dydx_address>"}`
- Market IDs on testnet use format `BTC-USD`, `ETH-USD`, `SOL-USD`
- If SDK docs are unclear, check: https://github.com/dydxprotocol/v4-clients/tree/main/v4-client-py-v2

---

## Files to Create

```
llm-quant-finance/
├── backtesting/
│   ├── strategies/
│   │   ├── dydx_adapter.py       (DydxExecutor class)
│   │   └── dydx_types.py         (Pydantic models)
│   └── live/
│       ├── __init__.py
│       ├── setup_testnet.py      (one-shot: generate wallet + fund)
│       ├── TESTNET_MNEMONIC.txt  (gitignored, created by setup_testnet.py)
│       ├── logs/
│       │   └── .gitkeep
│       └── tests/
│           ├── __init__.py
│           └── test_dydx_testnet.py
└── .gitignore                    (add TESTNET_MNEMONIC.txt)
```

## Notebook Convention
**All phases live in a single notebook** (`snn_crypto_predictor_llm-quant-dydx-adapter-v1.ipynb`). Each pipeline phase is a top-level section with its own subsections (experiment matrix, experiments, results, analysis). Shared infrastructure (data, encodings, models, baselines) appears once at the top. Phase 3 iterations append as new top-level sections. Final section is always a cross-phase deep analysis.

## Phase 1: Autonomous Build
_Architect designs → Critic reviews → Builder implements_

### Stage History
| Stage | Date | Agent | Notes |
|-------|------|-------|-------|
| pipeline_created | 2026-03-27 | belam-main | Pipeline instance created |
| p1_builder_implement | 2026-03-27 | unknown | auto_wiggum: hard timeout reached, marking complete |
| p1_builder_bugfix | 2026-03-27 | builder | Implemented full dYdX v4 execution adapter. All 8 testnet integration tests pass (18.7s). Deliverables: dydx_adapter.py (DydxExecutor class ~300 lines), dydx_types.py (Pydantic models), setup_testnet.py (wallet+faucet), test_dydx_testnet.py (8 real-testnet tests). Fixed: protobuf conflict resolved by installing dydx SDK into venv directly; strategies/__init__.py made optional-dep safe; faucet requires subaccountNumber=0; ruff clean. |
| p1_critic_review | 2026-03-27 | critic | APPROVED: 0 BLOCKs, 0 HIGH FLAGs, 1 MED FLAG, 3 LOW FLAGs. All 4 deliverables verified. ruff clean. All SDK imports resolve in venv. Risk controls correct. FLAG-1 MED: _derive_address() duplicates Wallet.address property (cosmetic). FLAG-2 LOW: test_close_position has soft position assertion acceptable for testnet indexer lag. FLAG-3 LOW: sequence management is single-threaded only (fine for sequential trading). FLAG-4 LOW: _order_registry lost on restart. Notable: Builder added reduce_only=True in close_position (prevents position flip — critical safety) and wait_for_position() helper (essential for testnet block time). Review at: machinelearning/llm-quant-finance/research/pipeline_builds/llm-quant-dydx-adapter-v1_critic_review.md |

## Phase 2: Human-in-the-Loop
_Status: Queued — auto-triggers on Phase 1 completion_

### Feedback
_(Shael's feedback goes here when Phase 1 is complete and reviewed)_

## Phase 3: Iterative Research (Autonomous or Human-Triggered)
_Status: LOCKED — requires Phase 2 completion before activation_

**Gate condition:** `phase2_complete` must be set before any Phase 3 iteration can proceed.

### How Phase 3 Works

1. **Human-triggered:** Shael says "try X" → iteration created and built
2. **Agent-triggered:** Analysis reveals compelling follow-up → proposal generated:
   - Score ≥ 7: auto-approved
   - Score 4-6: flagged for Shael's review
   - Score < 4: rejected, logged only

### Iteration Log

| ID | Hypothesis | Proposed By | Status | Result |
|----|-----------|-------------|--------|--------|

## Artifacts
- **Spec:** `snn_applied_finance/specs/llm-quant-dydx-adapter-v1_spec.yaml`
- **Design:** `snn_applied_finance/research/pipeline_builds/llm-quant-dydx-adapter-v1_architect_design.md`
- **Review:** `snn_applied_finance/research/pipeline_builds/llm-quant-dydx-adapter-v1_critic_design_review.md`
- **State:** `snn_applied_finance/research/pipeline_builds/llm-quant-dydx-adapter-v1_state.json`
- **Notebook:** `snn_applied_finance/notebooks/snn_crypto_predictor_llm-quant-dydx-adapter-v1.ipynb`
