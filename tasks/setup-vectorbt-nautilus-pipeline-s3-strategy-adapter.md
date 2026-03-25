---
primitive: task
status: in_pipeline
priority: medium
owner: builder
tags: [backtesting, infrastructure, strategy]
pipeline: setup-vectorbt-nautilus-pipeline-s3-strategy-adapter
project: snn-applied-finance
estimate: 6 hours
parent_task: setup-vectorbt-nautilus-pipeline
depends_on: [setup-vectorbt-nautilus-pipeline-s2-data-pipeline]
upstream: [task/setup-vectorbt-nautilus-pipeline-s2-data-pipeline]
---

# S3: Strategy Adapter — Unified Interface for VectorBT + NautilusTrader

## Scope

- Design an abstract strategy interface that compiles to both VectorBT's vectorized N-dimensional NumPy arrays and NautilusTrader's event-driven `on_bar()` paradigm
- Implement one reference strategy (dual moving average crossover) proving identical outputs
- Provide a comparison harness that verifies trade logs match between frameworks
- Establish the pattern all future strategies will follow

## Implementation Details

### File Structure

```
machinelearning/snn_applied_finance/backtesting/strategies/
├── __init__.py
├── base.py                # Abstract base class
├── adapters/
│   ├── __init__.py
│   ├── vectorbt_adapter.py    # Compiles strategy → VectorBT signals
│   └── nautilus_adapter.py    # Wraps strategy → NautilusTrader Strategy
├── reference/
│   ├── __init__.py
│   └── dual_ma_crossover.py   # Reference implementation
└── comparison.py              # Cross-framework trade log comparison
```

### Abstract Base Class: `base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
import numpy as np
import polars as pl


@dataclass
class StrategyParams:
    """Base class for strategy parameters. Subclass per strategy."""
    pass


@dataclass
class Signal:
    """Unified signal representation."""
    timestamp: Any  # datetime
    direction: int  # 1 = long entry, -1 = short entry, 0 = exit
    size: float = 1.0


class DualModeStrategy(ABC):
    """
    Abstract strategy that supports both vectorized and event-driven execution.
    
    Contract:
    - generate_signals() produces the SAME trades as iterating on_bar() over the same data
    - Parameters are identical in both modes
    - The strategy is stateless between calls to generate_signals()
      but maintains state across on_bar() calls (as NautilusTrader requires)
    """

    @abstractmethod
    def parameters(self) -> StrategyParams:
        """Return current strategy parameters."""
        ...

    @abstractmethod
    def generate_signals(self, ohlcv: pl.DataFrame) -> np.ndarray:
        """
        Vectorized signal generation for VectorBT.
        
        Args:
            ohlcv: Polars DataFrame with columns [timestamp, open, high, low, close, volume]
        
        Returns:
            np.ndarray of shape (n_rows,) with values:
                1  = long entry signal
               -1  = short entry / exit signal (depending on strategy)
                0  = no signal
        
        This method MUST be deterministic and produce identical results
        to iterating on_bar() over the same data.
        """
        ...

    @abstractmethod
    def on_bar(self, bar: dict) -> Signal | None:
        """
        Event-driven signal generation for NautilusTrader.
        
        Args:
            bar: dict with keys {timestamp, open, high, low, close, volume}
        
        Returns:
            Signal if a trade should occur, None otherwise
        
        The strategy maintains internal state between calls.
        Call reset() before processing a new dataset.
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset internal state for event-driven mode."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy identifier string."""
        ...
```

### Reference Strategy: `dual_ma_crossover.py`

Implement a simple dual moving average crossover:

```python
@dataclass
class DualMACrossoverParams(StrategyParams):
    fast_window: int = 10
    slow_window: int = 30


class DualMACrossover(DualModeStrategy):
    def __init__(self, fast_window: int = 10, slow_window: int = 30):
        self._params = DualMACrossoverParams(fast_window, slow_window)
        self._state = {}  # For event-driven mode
        self.reset()

    def generate_signals(self, ohlcv: pl.DataFrame) -> np.ndarray:
        close = ohlcv["close"].to_numpy()
        fast_ma = _rolling_mean(close, self._params.fast_window)
        slow_ma = _rolling_mean(close, self._params.slow_window)
        
        signals = np.zeros(len(close), dtype=np.int8)
        # Entry: fast crosses above slow
        # Exit: fast crosses below slow
        prev_above = False
        for i in range(self._params.slow_window, len(close)):
            above = fast_ma[i] > slow_ma[i]
            if above and not prev_above:
                signals[i] = 1   # Long entry
            elif not above and prev_above:
                signals[i] = -1  # Exit
            prev_above = above
        return signals

    def on_bar(self, bar: dict) -> Signal | None:
        self._state["prices"].append(bar["close"])
        prices = self._state["prices"]
        
        if len(prices) < self._params.slow_window:
            return None
        
        fast_ma = np.mean(prices[-self._params.fast_window:])
        slow_ma = np.mean(prices[-self._params.slow_window:])
        
        above = fast_ma > slow_ma
        prev_above = self._state.get("prev_above")
        self._state["prev_above"] = above
        
        if prev_above is None:
            return None
        if above and not prev_above:
            return Signal(timestamp=bar["timestamp"], direction=1)
        elif not above and prev_above:
            return Signal(timestamp=bar["timestamp"], direction=-1)
        return None
```

**Critical implementation note:** Both `generate_signals()` and `on_bar()` MUST use the same rolling mean calculation. Don't use Pandas `.rolling()` in one and NumPy in the other — subtle differences in edge handling will cause mismatches. Implement a single `_rolling_mean()` helper used by both paths.

### VectorBT Adapter: `vectorbt_adapter.py`

```python
def run_vectorbt_backtest(strategy: DualModeStrategy, ohlcv: pl.DataFrame, **pf_kwargs) -> dict:
    """
    Run strategy through VectorBT and return standardized trade log.
    
    Steps:
    1. Call strategy.generate_signals(ohlcv) to get signal array
    2. Convert signals to VectorBT entries/exits:
       entries = signals == 1
       exits = signals == -1
    3. Convert ohlcv to pandas (VectorBT requirement)
    4. Run vbt.Portfolio.from_signals(close, entries, exits, **pf_kwargs)
    5. Extract trade log: pf.trades.records_readable
    6. Return standardized dict with trades list
    """
```

### NautilusTrader Adapter: `nautilus_adapter.py`

```python
from nautilus_trader.trading.strategy import Strategy as NautilusStrategy
from nautilus_trader.config import StrategyConfig


class NautilusStrategyWrapper(NautilusStrategy):
    """
    Wraps a DualModeStrategy for NautilusTrader execution.
    
    Key methods to implement:
    - on_start(): Subscribe to bars
    - on_bar(bar: Bar): Call self.strategy.on_bar(), submit orders
    - on_stop(): Flatten positions
    """

    def __init__(self, config: StrategyConfig, strategy: DualModeStrategy):
        super().__init__(config)
        self.strategy = strategy

    def on_bar(self, bar):
        bar_dict = {
            "timestamp": bar.ts_event,
            "open": float(bar.open),
            "high": float(bar.high),
            "low": float(bar.low),
            "close": float(bar.close),
            "volume": float(bar.volume),
        }
        signal = self.strategy.on_bar(bar_dict)
        if signal and signal.direction == 1:
            # Submit market buy order
            ...
        elif signal and signal.direction == -1:
            # Close position
            ...


def run_nautilus_backtest(strategy: DualModeStrategy, ohlcv: pl.DataFrame, **kwargs) -> dict:
    """
    Run strategy through NautilusTrader and return standardized trade log.
    
    Steps:
    1. Create BacktestEngine with appropriate venue config
    2. Add instrument (crypto perpetual or spot)
    3. Add bar data converted from ohlcv
    4. Create NautilusStrategyWrapper with the strategy
    5. Run engine
    6. Extract trade log from engine.trader reports
    7. Return standardized dict matching VectorBT output format
    """
```

**NautilusTrader gotchas:**
- Need to configure a venue (e.g., `Venue("BINANCE")`) with proper fee model
- Instrument must be created with correct price/size precision and tick sizes
- Bar data must be added as `BarType` objects with proper specifications
- For fair comparison, use `OmsType.HEDGING` or `OmsType.NETTING` consistently
- Set initial account balance explicitly

### Comparison Harness: `comparison.py`

```python
def compare_trade_logs(vbt_trades: dict, nautilus_trades: dict,
                       price_tolerance: float = 1e-6,
                       time_tolerance_seconds: int = 0) -> ComparisonResult:
    """
    Compare trade logs from both frameworks.
    
    Checks:
    1. Same number of trades
    2. Same entry/exit timestamps (within tolerance)
    3. Same direction (long/short)
    4. Same entry/exit prices (within tolerance — should be exact for market orders on same data)
    5. Same P&L per trade (within tolerance for floating point)
    
    Returns ComparisonResult with pass/fail and detailed diffs.
    """
```

### Test File: `tests/test_strategy_adapter.py`

```python
class TestDualModeEquivalence:
    """The core contract: both modes produce identical trades."""
    
    def test_signals_match_on_bar(self):
        """generate_signals() and iterating on_bar() produce same signals."""
        strategy = DualMACrossover(fast_window=10, slow_window=30)
        ohlcv = load_test_data()  # 500+ rows of BTC daily
        
        vectorized = strategy.generate_signals(ohlcv)
        
        strategy.reset()
        event_driven = []
        for row in ohlcv.iter_rows(named=True):
            signal = strategy.on_bar(row)
            event_driven.append(signal.direction if signal else 0)
        
        np.testing.assert_array_equal(vectorized, np.array(event_driven))

    def test_vbt_nautilus_trade_logs_match(self):
        """Full backtest in both frameworks produces identical trade logs."""
        strategy = DualMACrossover()
        ohlcv = load_test_data()
        
        vbt_result = run_vectorbt_backtest(strategy, ohlcv)
        nautilus_result = run_nautilus_backtest(strategy, ohlcv)
        
        comparison = compare_trade_logs(vbt_result, nautilus_result)
        assert comparison.passed, f"Trade logs differ: {comparison.diffs}"
```

## Success Criteria

- Reference strategy (dual MA crossover) produces identical signal arrays from `generate_signals()` and sequential `on_bar()` calls
- Full backtest through VectorBT and NautilusTrader produces matching trade logs (same entries, exits, directions, prices)
- `pytest tests/test_strategy_adapter.py` passes
- Abstract base class is clean and extensible for future strategies
- Comparison harness produces clear diff output when logs don't match

## References

- Decision: `d: two-phase-backtest-workflow` — same strategy, two execution modes
- Knowledge: VectorBT PRO (strategies as N-dimensional NumPy arrays), NautilusTrader (same codepath backtest/live)
- [VectorBT Portfolio.from_signals](https://vectorbt.pro/pvt_a43e30e7/api/portfolio/base/#vectorbtpro.portfolio.base.Portfolio.from_signals)
- [NautilusTrader Strategy class](https://nautilustrader.io/docs/api_reference/trading/strategy)
- [NautilusTrader BacktestEngine](https://nautilustrader.io/docs/api_reference/backtest/engine)
