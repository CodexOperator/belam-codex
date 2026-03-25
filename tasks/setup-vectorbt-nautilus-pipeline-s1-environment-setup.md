---
primitive: task
status: open
priority: medium
owner: builder
tags: [backtesting, infrastructure]
project: snn-applied-finance
estimate: 4 hours
parent_task: setup-vectorbt-nautilus-pipeline
depends_on: []
upstream: []
---

# S1: Environment Setup — VectorBT PRO + NautilusTrader Stack

## Scope

- Install and pin all core dependencies: VectorBT PRO, NautilusTrader, Polars, fracdiff, arch, skfolio, DuckDB, and supporting libraries
- Create the `machinelearning/snn_applied_finance/backtesting/` directory structure with proper `__init__.py` files
- Write smoke tests verifying all imports, version checks, and trivial backtest execution in both frameworks
- Generate a locked `requirements.txt` for reproducible builds

## Implementation Details

### Directory Structure

Create this layout under the workspace root:

```
machinelearning/snn_applied_finance/backtesting/
├── __init__.py
├── data/                  # s2 will populate
│   └── __init__.py
├── strategies/            # s3 will populate
│   └── __init__.py
├── validation/            # s4, s6 will populate
│   └── __init__.py
├── costs/                 # s5 will populate
│   └── __init__.py
└── utils/
    └── __init__.py
tests/
└── test_backtest_env.py
```

### Dependencies

Pin these in `requirements.txt` (use latest stable at build time):

```
vectorbtpro>=2.0          # VectorBT PRO — check license/install method
nautilus_trader>=1.200     # NautilusTrader — Rust core, pip install works
polars>=1.0                # DataFrame engine, replaces Pandas for large data
duckdb>=1.0                # Embedded analytics DB, Parquet-native
fracdiff>=0.9              # Fractional differentiation (Marcos López de Prado)
arch>=7.0                  # ARCH/GARCH models, statistical tests
skfolio>=0.5               # Portfolio optimization with CombinatorialPurgedCV
numba>=0.60                # JIT compilation (VectorBT dependency)
numpy>=1.26               # Array engine
scipy>=1.13               # Statistical functions
pytest>=8.0                # Test runner
```

**Gotchas:**
- VectorBT PRO requires a license key. Check if `VECTORBTPRO_LICENSE` env var is set, or if it's installed from a private index. The smoke test should gracefully report "VectorBT PRO not licensed" rather than hard-fail if the key is missing — but the test should still verify the import works.
- NautilusTrader has Rust compilation requirements. On Linux ARM64 (our host), `pip install nautilus_trader` should provide pre-built wheels. If not, ensure Rust toolchain is available.
- `fracdiff` may need `cython` at build time.
- Use a virtual environment if one doesn't already exist. Check for existing venv at `~/.openclaw/workspace/.venv` or create one.

### Smoke Test: `tests/test_backtest_env.py`

```python
"""Smoke tests for backtest environment setup."""
import pytest


class TestImports:
    """Verify all required packages import successfully."""

    def test_vectorbt_import(self):
        import vectorbtpro as vbt
        assert hasattr(vbt, '__version__')

    def test_nautilus_import(self):
        from nautilus_trader.backtest.engine import BacktestEngine
        from nautilus_trader.config import BacktestEngineConfig
        assert BacktestEngine is not None

    def test_polars_import(self):
        import polars as pl
        assert hasattr(pl, 'DataFrame')

    def test_duckdb_import(self):
        import duckdb
        conn = duckdb.connect(':memory:')
        result = conn.execute('SELECT 1').fetchone()
        assert result == (1,)
        conn.close()

    def test_fracdiff_import(self):
        import fracdiff
        assert hasattr(fracdiff, 'fdiff')

    def test_arch_import(self):
        from arch import arch_model
        assert arch_model is not None

    def test_skfolio_import(self):
        from skfolio.model_selection import CombinatorialPurgedCV
        assert CombinatorialPurgedCV is not None

    def test_numba_import(self):
        import numba
        assert hasattr(numba, 'jit')


class TestTrivialBacktest:
    """Verify frameworks can execute minimal backtests."""

    def test_vectorbt_trivial(self):
        """VectorBT can run a simple moving average crossover."""
        import vectorbtpro as vbt
        import numpy as np

        # Generate synthetic price data
        np.random.seed(42)
        close = np.cumsum(np.random.randn(200)) + 100

        # Simple fast/slow MA crossover signals
        fast_ma = vbt.MA.run(close, window=10)
        slow_ma = vbt.MA.run(close, window=30)

        entries = fast_ma.ma_crossed_above(slow_ma)
        exits = fast_ma.ma_crossed_below(slow_ma)

        pf = vbt.Portfolio.from_signals(close, entries, exits)
        stats = pf.stats()
        assert stats is not None
        assert 'Total Return [%]' in stats.index or len(stats) > 0

    def test_nautilus_engine_instantiation(self):
        """NautilusTrader BacktestEngine can be created."""
        from nautilus_trader.backtest.engine import BacktestEngine
        from nautilus_trader.config import BacktestEngineConfig

        config = BacktestEngineConfig(
            trader_id="TESTER-001",
        )
        engine = BacktestEngine(config=config)
        assert engine is not None
        engine.dispose()


class TestDirectoryStructure:
    """Verify directory structure exists."""

    def test_backtesting_package(self):
        from pathlib import Path
        base = Path(__file__).parent.parent / "machinelearning" / "snn_applied_finance" / "backtesting"
        assert base.exists(), f"Missing: {base}"
        for subdir in ["data", "strategies", "validation", "costs", "utils"]:
            assert (base / subdir).exists(), f"Missing: {base / subdir}"
            assert (base / subdir / "__init__.py").exists(), f"Missing __init__.py in {subdir}"
```

### Installation Steps

1. Create/activate venv
2. `pip install -r requirements.txt`
3. Verify VectorBT PRO license (warn if missing, don't block)
4. Create directory structure with `__init__.py` files
5. Run `pytest tests/test_backtest_env.py -v`

## Success Criteria

- `pytest tests/test_backtest_env.py` passes — all imports succeed, version checks pass, trivial backtest runs in VectorBT, NautilusTrader engine instantiates
- `requirements.txt` exists with pinned versions
- Directory structure `machinelearning/snn_applied_finance/backtesting/{data,strategies,validation,costs,utils}/` exists with `__init__.py` files
- No import errors or missing dependencies

## References

- Decision: `d: two-phase-backtest-workflow` — VectorBT PRO for discovery, NautilusTrader for validation
- Knowledge: VectorBT PRO (Numba JIT, N-dimensional arrays), NautilusTrader (Rust core + Python API)
- [VectorBT PRO docs](https://vectorbt.pro/)
- [NautilusTrader docs](https://nautilustrader.io/)
- [skfolio docs](https://skfolio.org/)
