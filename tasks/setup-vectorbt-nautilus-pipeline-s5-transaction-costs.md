---
primitive: task
status: open
priority: medium
owner: builder
tags: [backtesting, infrastructure, costs]
project: snn-applied-finance
estimate: 5 hours
parent_task: setup-vectorbt-nautilus-pipeline
depends_on: [setup-vectorbt-nautilus-pipeline-s3-strategy-adapter]
upstream: [task/setup-vectorbt-nautilus-pipeline-s3-strategy-adapter]
---

# S5: Transaction Cost Models — Square-Root Impact + Linear Costs

## Scope

- Implement the 3/2-power (square-root) market impact model per Cvxportfolio empirical findings
- Implement linear cost model (fixed bps) for comparison
- Wire cost models into VectorBT via custom cost functions
- Wire cost models into NautilusTrader via fill model configuration
- Make spread, slippage, and impact coefficients configurable per asset

## Implementation Details

### File Structure

```
machinelearning/snn_applied_finance/backtesting/costs/
├── __init__.py
├── models.py              # Cost model implementations
├── vectorbt_costs.py      # VectorBT integration
├── nautilus_costs.py       # NautilusTrader fill model integration
└── config.py              # Per-asset cost configuration
```

### Cost Models: `models.py`

#### Linear Cost Model

```python
def linear_cost(trade_value: float, bps: float = 3.0) -> float:
    """
    Simple linear transaction cost.
    
    cost = bps/10000 * |trade_value|
    
    Typical values:
    - Binance maker: 1 bps (with BNB discount)
    - Binance taker: 3-5 bps
    - Institutional: 1-2 bps
    """
    return (bps / 10_000) * abs(trade_value)
```

#### Square-Root (3/2-Power) Impact Model

```python
def sqrt_impact_cost(trade_value: float, daily_volume: float,
                     sigma: float, a: float = 0.01, b: float = 0.1) -> float:
    """
    Square-root market impact model (Cvxportfolio best empirical fit).
    
    Total cost = linear_component + impact_component
    
    linear_component = a * |trade_value|
        - Covers spread + exchange fees
        - a ≈ 0.5-5 bps typically
    
    impact_component = b * sigma * |trade_value|^(3/2) / daily_volume^(1/2)
        - Models temporary market impact
        - sigma: daily volatility of the asset
        - b: impact coefficient (calibrate per asset class)
        - Scales with trade size^1.5 / sqrt(volume) — large trades in illiquid
          markets cost disproportionately more
    
    The 3/2 power law is the best empirical fit found by Boyd et al. (Cvxportfolio),
    outperforming both linear and pure square-root models on real equity data.
    Crypto markets are less liquid, so impact coefficients should be larger.
    
    Args:
        trade_value: absolute dollar value of the trade
        daily_volume: average daily dollar volume of the asset
        sigma: daily return volatility (e.g., 0.03 for 3% daily vol)
        a: linear coefficient (spread + fees)
        b: impact coefficient
    
    Returns:
        Total cost in dollars
    """
    linear = a * abs(trade_value)
    impact = b * sigma * (abs(trade_value) ** 1.5) / (daily_volume ** 0.5)
    return linear + impact
```

**Calibration guidance for crypto:**
- BTC: `a=0.0003` (3 bps), `b=0.05-0.15`, `sigma` from GARCH or rolling 30-day vol
- ETH: `a=0.0005`, `b=0.10-0.20` (less liquid)
- SOL: `a=0.0008`, `b=0.15-0.30` (significantly less liquid)
- These are starting estimates — proper calibration requires fitting to actual execution data

### Per-Asset Configuration: `config.py`

```python
from dataclasses import dataclass


@dataclass
class AssetCostConfig:
    """Transaction cost configuration for a single asset."""
    symbol: str
    linear_bps: float = 3.0           # Linear model: cost in basis points
    spread_bps: float = 1.0           # Half-spread in bps
    slippage_bps: float = 1.0         # Expected slippage in bps
    impact_a: float = 0.0003          # Linear coefficient for sqrt model
    impact_b: float = 0.10            # Impact coefficient for sqrt model
    avg_daily_volume: float = 1e9     # Average daily volume in USD
    daily_volatility: float = 0.03    # Daily return vol (σ)


# Default configurations
DEFAULT_CONFIGS = {
    "BTCUSDT": AssetCostConfig(
        symbol="BTCUSDT", linear_bps=3.0, spread_bps=0.5,
        slippage_bps=0.5, impact_a=0.0003, impact_b=0.08,
        avg_daily_volume=15e9, daily_volatility=0.025
    ),
    "ETHUSDT": AssetCostConfig(
        symbol="ETHUSDT", linear_bps=3.0, spread_bps=1.0,
        slippage_bps=1.0, impact_a=0.0005, impact_b=0.12,
        avg_daily_volume=5e9, daily_volatility=0.035
    ),
    "SOLUSDT": AssetCostConfig(
        symbol="SOLUSDT", linear_bps=5.0, spread_bps=2.0,
        slippage_bps=2.0, impact_a=0.0008, impact_b=0.20,
        avg_daily_volume=1e9, daily_volatility=0.05
    ),
}
```

### VectorBT Integration: `vectorbt_costs.py`

VectorBT PRO supports custom cost functions via `Portfolio.from_signals()`:

```python
import vectorbtpro as vbt
import numpy as np
from numba import njit


@njit
def linear_cost_func(col, i, val, price, fees, fixed_fees, slippage):
    """
    Numba-JIT custom cost function for VectorBT.
    
    VectorBT calls this per trade with:
    - col: column index (parameter combo)
    - i: row index (time step)
    - val: trade value (positive = buy, negative = sell)
    - price: execution price
    - fees: configured fee rate
    - fixed_fees: configured fixed fee
    - slippage: configured slippage
    
    Return: total cost as fraction of trade value
    """
    return abs(val) * fees + fixed_fees


def create_vbt_cost_model(config: AssetCostConfig, model: str = "linear") -> dict:
    """
    Create VectorBT-compatible cost parameters.
    
    For 'linear' model:
        Return dict with fees=bps/10000 and slippage=slippage_bps/10000
    
    For 'sqrt_impact' model:
        VectorBT doesn't natively support volume-dependent costs.
        Two approaches:
        1. Pre-compute cost per bar as a cost array, pass via `fees` as array
        2. Use a custom Numba function (limited — can't access volume in standard API)
        
        Recommended: Approach 1 — pre-compute expected cost per bar given
        typical trade size, and pass as fees array.
    
    Returns dict of kwargs for vbt.Portfolio.from_signals()
    """
    if model == "linear":
        return {
            "fees": config.linear_bps / 10_000,
            "slippage": config.slippage_bps / 10_000,
            "fixed_fees": 0.0,
        }
    elif model == "sqrt_impact":
        # Pre-computation approach: estimate cost for a reference trade size
        # The caller should provide trade_size or portfolio_value
        # Return a function that generates the fees array
        ...
```

**VectorBT gotcha:** VectorBT's `fees` parameter can be:
- A scalar (constant percentage)
- A 1D array (per-bar percentage)
- A 2D array (per-bar × per-column)

For the sqrt impact model, pre-compute a per-bar cost estimate assuming a reference trade size (e.g., 1% of portfolio) and pass as a 1D array. This is an approximation — the actual cost depends on trade size, which is circular. Document this limitation.

### NautilusTrader Integration: `nautilus_costs.py`

NautilusTrader uses `FeeModel` and `FillModel` for cost simulation:

```python
from nautilus_trader.backtest.models import FillModel, MakerTakerFeeModel
from nautilus_trader.model.objects import Money


def create_nautilus_fee_model(config: AssetCostConfig) -> MakerTakerFeeModel:
    """
    Create NautilusTrader fee model from cost config.
    
    MakerTakerFeeModel parameters:
    - maker_fee: Decimal (e.g., 0.0001 for 1 bps)
    - taker_fee: Decimal (e.g., 0.0003 for 3 bps)
    """
    from decimal import Decimal
    return MakerTakerFeeModel(
        maker_fee=Decimal(str(config.spread_bps / 10_000)),
        taker_fee=Decimal(str(config.linear_bps / 10_000)),
    )


def create_nautilus_fill_model(config: AssetCostConfig) -> FillModel:
    """
    Create NautilusTrader fill model with slippage.
    
    FillModel controls:
    - prob_fill_on_limit: probability limit orders fill (default 1.0 for backtest)
    - prob_fill_on_stop: probability stop orders fill
    - prob_slippage: probability of slippage occurring
    - random_seed: for reproducibility
    
    For market impact modeling: NautilusTrader's SimulatedExchange supports
    custom latency models. For sqrt impact, consider subclassing FillModel
    or applying cost adjustment post-backtest.
    """
    return FillModel(
        prob_fill_on_limit=1.0,
        prob_fill_on_stop=1.0,
        prob_slippage=1.0,  # Always apply slippage in backtest
        random_seed=42,
    )
```

**NautilusTrader limitation:** The built-in fill models don't directly support volume-dependent impact. For the sqrt model in Nautilus, implement a post-trade cost adjustment:

```python
def adjust_nautilus_pnl_for_impact(trades: list, volume_data: pl.DataFrame,
                                    config: AssetCostConfig) -> list:
    """
    Post-hoc adjustment of NautilusTrader trade P&L for market impact.
    
    For each trade:
    1. Look up daily volume at trade timestamp
    2. Compute sqrt_impact_cost for the trade size
    3. Subtract from trade P&L
    
    This is an approximation but preserves NautilusTrader's execution model
    while adding realistic impact costs.
    """
```

### Test File: `tests/test_transaction_costs.py`

```python
class TestCostModels:
    def test_linear_cost_basic(self):
        """3 bps on $10,000 trade = $3."""
        assert linear_cost(10_000, bps=3.0) == pytest.approx(3.0)

    def test_sqrt_impact_scales_superlinearly(self):
        """Doubling trade size should more than double impact cost."""
        cost_small = sqrt_impact_cost(10_000, 1e9, 0.03)
        cost_large = sqrt_impact_cost(20_000, 1e9, 0.03)
        assert cost_large > 2 * cost_small  # 3/2 power → 2^1.5 ≈ 2.83x

    def test_vbt_with_without_costs(self):
        """Backtest with costs has lower total return than without."""
        ...

    def test_nautilus_with_without_costs(self):
        """Same for NautilusTrader."""
        ...

    def test_cost_parity_between_frameworks(self):
        """Both frameworks produce similar total costs on same trades."""
        # Allow tolerance for implementation differences
        ...
```

## Success Criteria

- Both cost models (linear, sqrt impact) correctly compute expected values
- VectorBT backtest with costs shows realistic P&L reduction vs. zero-cost backtest
- NautilusTrader backtest with costs shows realistic P&L reduction
- Cost impact is comparable between frameworks (within 10% tolerance for sqrt model due to approximations)
- Per-asset configuration is clean and extensible
- `pytest tests/test_transaction_costs.py` passes
- Doubling trade size in sqrt model increases cost by ~2.83x (validates 3/2 power law)

## References

- Decision: `d: two-phase-backtest-workflow`
- Knowledge: Transaction costs — linear (1-5 bps), quadratic market impact, 3/2-power (Cvxportfolio best empirical fit)
- [Cvxportfolio — Multi-Period Trading via Convex Optimization](https://web.stanford.edu/~boyd/papers/cvx_portfolio.html) — Boyd et al., 3/2-power impact model
- [VectorBT custom fees](https://vectorbt.pro/pvt_a43e30e7/api/portfolio/base/)
- [NautilusTrader fee models](https://nautilustrader.io/docs/api_reference/backtest/models)
- Almgren & Chriss (2001) — Optimal execution of portfolio transactions (foundational market impact)
