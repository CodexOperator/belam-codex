---
primitive: task
status: in_pipeline
priority: medium
owner: builder
tags: [backtesting, validation, statistics]
pipeline: setup-vectorbt-nautilus-pipeline-s4-walk-forward-validation
project: snn-applied-finance
estimate: 5 hours
parent_task: setup-vectorbt-nautilus-pipeline
depends_on: [setup-vectorbt-nautilus-pipeline-s3-strategy-adapter]
upstream: [task/setup-vectorbt-nautilus-pipeline-s3-strategy-adapter]
---

# S4: Walk-Forward Validation with Combinatorial Purged Cross-Validation

## Scope

- Integrate skfolio's `CombinatorialPurgedCV` with VectorBT parameter sweep output
- Implement purged K-fold CV with minimum 7 folds and configurable embargo gap
- Generate walk-forward analysis reports: per-fold Sharpe, aggregate metrics, fold stability
- Provide a reusable validation pipeline that any strategy can plug into

## Implementation Details

### File Structure

```
machinelearning/snn_applied_finance/backtesting/validation/
├── __init__.py
├── walk_forward.py          # CombinatorialPurgedCV integration
├── metrics.py               # Per-fold and aggregate metric computation
├── report.py                # Report generation (structured dict + optional HTML/JSON)
└── config.py                # Validation configuration dataclass
```

### Configuration: `config.py`

```python
from dataclasses import dataclass, field


@dataclass
class WalkForwardConfig:
    """Configuration for walk-forward validation."""
    n_folds: int = 7                    # Minimum 7 per statistical hygiene requirements
    n_test_folds: int = 2               # Number of test folds in combinatorial split
    embargo_periods: int = 5            # Gap between train/test to prevent leakage
    purge_periods: int = 0              # Additional purge (typically 0 if embargo is set)
    min_train_size: int = 100           # Minimum training samples per fold
    metrics: list[str] = field(default_factory=lambda: [
        "sharpe_ratio", "sortino_ratio", "max_drawdown",
        "total_return", "calmar_ratio", "win_rate"
    ])
```

### Core Module: `walk_forward.py`

```python
from skfolio.model_selection import CombinatorialPurgedCV


class WalkForwardValidator:
    """
    Runs combinatorial purged cross-validation on strategy parameter sweep results.
    
    Workflow:
    1. Accept VectorBT parameter sweep output (returns matrix indexed by time × params)
    2. Set up CombinatorialPurgedCV splitter
    3. For each train/test split:
       a. Identify best params on train fold (by Sharpe or configured metric)
       b. Evaluate those params on test fold
       c. Record per-fold metrics
    4. Aggregate results across all combinatorial splits
    """

    def __init__(self, config: WalkForwardConfig):
        self.config = config
        self.splitter = CombinatorialPurgedCV(
            n_folds=config.n_folds,
            n_test_folds=config.n_test_folds,
            embargo_td=config.embargo_periods,  # Note: check skfolio API for exact param name
        )

    def validate(self, returns_matrix: np.ndarray, timestamps: np.ndarray,
                 param_grid: list[dict]) -> WalkForwardResult:
        """
        Args:
            returns_matrix: shape (n_timesteps, n_param_combos) — daily returns 
                           for each parameter combination
            timestamps: shape (n_timesteps,) — datetime index
            param_grid: list of param dicts, one per column in returns_matrix
        
        Returns:
            WalkForwardResult with per-fold and aggregate metrics
        """
        ...
```

**skfolio CombinatorialPurgedCV API notes:**

```python
from skfolio.model_selection import CombinatorialPurgedCV
import numpy as np

# CombinatorialPurgedCV generates ALL combinatorial train/test splits
# For n_folds=7, n_test_folds=2: C(7,2) = 21 unique test combinations
cv = CombinatorialPurgedCV(
    n_folds=7,
    n_test_folds=2,
    embargo_td=pd.Timedelta(days=5),  # embargo as timedelta
)

# Usage with sklearn-style interface:
# cv.split(X) yields (train_indices, test_indices)
for train_idx, test_idx in cv.split(X):
    train_returns = returns_matrix[train_idx]
    test_returns = returns_matrix[test_idx]
    # Select best params on train, evaluate on test
```

**Gotcha:** skfolio's `embargo_td` expects a `pd.Timedelta`, not an integer. Convert: `pd.Timedelta(days=config.embargo_periods)` for daily data, `pd.Timedelta(hours=config.embargo_periods)` for hourly.

**Gotcha:** The `X` passed to `cv.split()` must have a DatetimeIndex for the embargo to work correctly. Construct a dummy pandas DataFrame/Series with the right index.

### Integration with VectorBT Parameter Sweeps

VectorBT PRO can run parameter sweeps and return portfolio objects for each combination:

```python
import vectorbtpro as vbt

# Example: sweep fast_window × slow_window
fast_windows = np.arange(5, 50, 5)
slow_windows = np.arange(20, 100, 10)

# VectorBT creates a multi-dimensional portfolio
# Access returns: pf.returns() — shape (n_timesteps, n_fast, n_slow)
# Flatten to 2D: (n_timesteps, n_param_combos)

# The validator needs:
# 1. returns_matrix — reshape pf.returns().values to (T, N) where N = len(fast) * len(slow)
# 2. timestamps — pf.returns().index
# 3. param_grid — list of {"fast_window": x, "slow_window": y} for each column
```

Provide a helper function:

```python
def extract_sweep_returns(pf: vbt.Portfolio) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    """
    Extract returns matrix from VectorBT portfolio sweep result.
    Handles reshaping multi-dimensional parameter grids to 2D.
    Returns (returns_matrix, timestamps, param_grid).
    """
```

### Metrics Module: `metrics.py`

```python
def compute_fold_metrics(returns: np.ndarray, metric_names: list[str]) -> dict[str, float]:
    """
    Compute standard metrics on a returns series.
    
    Supported metrics:
    - sharpe_ratio: annualized, assuming 252 trading days (crypto: use 365)
    - sortino_ratio: downside deviation only
    - max_drawdown: maximum peak-to-trough decline
    - total_return: cumulative return over period
    - calmar_ratio: annualized return / max drawdown
    - win_rate: fraction of positive-return periods
    
    Use 365 annualization factor for crypto (trades 24/7/365).
    """
```

### Report Module: `report.py`

```python
@dataclass
class WalkForwardResult:
    config: WalkForwardConfig
    n_splits: int                            # Total combinatorial splits (e.g., 21 for C(7,2))
    per_fold_metrics: list[dict[str, float]] # One dict per split
    aggregate_metrics: dict[str, float]      # Mean across folds
    fold_stability: dict[str, float]         # Std dev of metrics across folds
    best_params_per_fold: list[dict]         # Which params won each fold
    param_stability: float                   # Fraction of folds selecting same top params
    is_vs_oos_degradation: dict[str, float]  # IS metric - OOS metric per metric name


def generate_report(result: WalkForwardResult) -> dict:
    """
    Generate structured validation report.
    
    Report includes:
    - Summary: n_folds, n_splits, overall pass/fail heuristic
    - Per-fold table: fold_id, train_period, test_period, best_params, sharpe, drawdown, etc.
    - Aggregate: mean Sharpe, mean drawdown, stability scores
    - Degradation analysis: how much do IS metrics degrade OOS?
    - Parameter stability: do the same params win across folds?
    
    Returns dict suitable for JSON serialization.
    Optional: also produce a simple text summary for logging.
    """
```

### Test File: `tests/test_walk_forward.py`

```python
class TestWalkForwardValidation:
    
    def test_splitter_produces_correct_fold_count(self):
        """7 folds, 2 test folds → C(7,2) = 21 splits."""
        config = WalkForwardConfig(n_folds=7, n_test_folds=2)
        validator = WalkForwardValidator(config)
        # Create dummy data with 700 daily observations
        n_splits = sum(1 for _ in validator.splitter.split(dummy_X))
        assert n_splits == 21

    def test_embargo_gap_applied(self):
        """Train and test indices don't overlap within embargo window."""
        ...

    def test_synthetic_overfit_detection(self):
        """
        Strategy that overfits (random signals optimized on train) should show
        large IS vs OOS degradation in the report.
        """
        ...

    def test_reference_strategy_validation(self):
        """Run full validation on dual MA crossover reference strategy."""
        strategy = DualMACrossover()
        # Run VectorBT sweep
        # Extract returns matrix
        # Run walk-forward validation
        # Check report has 7+ folds, all metrics populated
        result = validator.validate(returns_matrix, timestamps, param_grid)
        assert result.n_splits >= 21
        assert all(m in result.aggregate_metrics for m in config.metrics)
```

## Success Criteria

- `CombinatorialPurgedCV` runs with 7 folds, producing 21 combinatorial splits
- Embargo gap is correctly applied (no data leakage between train/test)
- Validation report includes: per-fold Sharpe, aggregate metrics, fold stability scores, IS vs OOS degradation
- Reference strategy (dual MA crossover) can be swept and validated end-to-end
- `pytest tests/test_walk_forward.py` passes

## References

- Decision: `d: two-phase-backtest-workflow`
- Knowledge: Purged K-Fold CV (7+ folds), statistical hygiene requirements
- Knowledge: skfolio (CombinatorialPurgedCV)
- [skfolio CombinatorialPurgedCV docs](https://skfolio.org/api_reference/model_selection/)
- [Marcos López de Prado — Advances in Financial Machine Learning, Ch. 12](https://www.wiley.com/en-us/Advances+in+Financial+Machine+Learning-p-9781119482086) — purged CV theory
- [VectorBT parameter optimization](https://vectorbt.pro/pvt_a43e30e7/tutorials/portfolio/optimization/)
