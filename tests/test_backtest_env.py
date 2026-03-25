#!/usr/bin/env python3
"""D3: Smoke tests for backtesting environment (S1).

Verifies all imports, version checks, and trivial backtest execution.
VectorBT PRO gracefully falls back to OSS if no license is available.
"""

import pytest
from pathlib import Path


class TestImports:
    """Verify all backtesting packages can be imported."""

    def test_vectorbt_import(self):
        """Try PRO first, fall back to OSS."""
        try:
            import vectorbtpro as vbt
            assert hasattr(vbt, '__version__')
        except ImportError:
            import vectorbt as vbt
            assert hasattr(vbt, '__version__')

    def test_nautilus_import(self):
        import nautilus_trader
        assert hasattr(nautilus_trader, '__version__')

    def test_polars_import(self):
        import polars as pl
        assert hasattr(pl, 'DataFrame')

    def test_duckdb_import(self):
        import duckdb
        conn = duckdb.connect(':memory:')
        result = conn.execute('SELECT 1').fetchone()
        assert result == (1,)
        conn.close()

    def test_fracdiff_shim(self):
        """fracdiff package incompatible with Python 3.12 — use our shim."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from machinelearning.snn_applied_finance.backtesting.utils.fracdiff_shim import fdiff
        import numpy as np
        result = fdiff(np.arange(100, dtype=float), d=0.5)
        assert len(result) == 100
        assert not np.isnan(result[-1])

    def test_arch_import(self):
        from arch import arch_model
        assert arch_model is not None

    def test_skfolio_import(self):
        from skfolio.optimization import MeanRisk
        assert MeanRisk is not None

    def test_numba_import(self):
        import numba
        assert hasattr(numba, 'jit')


class TestTrivialBacktest:
    """Verify frameworks can execute minimal backtests."""

    def test_vectorbt_trivial(self):
        """VectorBT can run a simple moving average crossover."""
        try:
            import vectorbtpro as vbt
        except ImportError:
            import vectorbt as vbt
        import numpy as np

        np.random.seed(42)
        close = np.cumsum(np.random.randn(200)) + 100

        fast_ma = vbt.MA.run(close, window=10)
        slow_ma = vbt.MA.run(close, window=30)

        entries = fast_ma.ma_crossed_above(slow_ma)
        exits = fast_ma.ma_crossed_below(slow_ma)

        pf = vbt.Portfolio.from_signals(close, entries, exits)
        stats = pf.stats()
        assert stats is not None
        assert len(stats) > 0

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
        base = Path(__file__).parent.parent / "machinelearning" / "snn_applied_finance" / "backtesting"
        assert base.exists(), f"Missing: {base}"
        for subdir in ["data", "strategies", "validation", "costs", "utils"]:
            assert (base / subdir).exists(), f"Missing: {base / subdir}"
            assert (base / subdir / "__init__.py").exists(), f"Missing __init__.py in {subdir}"
