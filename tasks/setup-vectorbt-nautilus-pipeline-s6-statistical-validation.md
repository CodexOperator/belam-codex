---
primitive: task
status: done
priority: medium
owner: builder
tags: [backtesting, validation, statistics]
pipeline: setup-vectorbt-nautilus-pipeline-s6-statistical-validation
project: snn-applied-finance
estimate: 5 hours
parent_task: setup-vectorbt-nautilus-pipeline
depends_on: [setup-vectorbt-nautilus-pipeline-s4-walk-forward-validation]
upstream: [task/setup-vectorbt-nautilus-pipeline-s4-walk-forward-validation]
---

# S6: Statistical Validation Gate — Deflated Sharpe Ratio + PBO

## Scope

- Implement Deflated Sharpe Ratio (DSR) correcting for selection bias, non-normal returns, and multiple testing
- Implement Probability of Backtest Overfitting (PBO) using combinatorial symmetric cross-validation (CSCV)
- Build an automated accept/reject gate with configurable thresholds
- Produce a structured validation report: DSR, PBO, pass/fail, confidence intervals

## Implementation Details

### File Structure

```
machinelearning/snn_applied_finance/backtesting/validation/
├── ... (existing from s4)
├── deflated_sharpe.py       # DSR implementation
├── pbo.py                   # Probability of Backtest Overfitting
├── gate.py                  # Automated accept/reject logic
└── validation_report.py     # Combined report generation
```

### Deflated Sharpe Ratio: `deflated_sharpe.py`

The DSR (Bailey & López de Prado, 2014) adjusts the observed Sharpe ratio for:
1. **Selection bias** — you tested N strategies and picked the best
2. **Non-normality** — skewness and kurtosis of returns
3. **Track record length** — shorter records have wider confidence intervals

```python
import numpy as np
from scipy import stats


def expected_max_sharpe(n_trials: int, variance: float = 1.0,
                        skewness: float = 0.0, kurtosis: float = 3.0) -> float:
    """
    Expected maximum Sharpe ratio from n_trials independent strategies,
    assuming returns drawn from a non-normal distribution.
    
    E[max(SR)] ≈ (1 - γ) * Φ^{-1}(1 - 1/N) + γ * Φ^{-1}(1 - 1/(N*e))
    
    where γ is the Euler-Mascheroni constant ≈ 0.5772
    
    Adjusted for non-normality:
    SR* = SR * [1 - skew/3 * SR + (kurt-3)/4 * SR^2]^{-1/2}
    
    From: Bailey & López de Prado (2014), "The Deflated Sharpe Ratio"
    """
    euler_mascheroni = 0.5772156649
    z1 = stats.norm.ppf(1 - 1/n_trials)
    z2 = stats.norm.ppf(1 - 1/(n_trials * np.e))
    e_max_sr = (1 - euler_mascheroni) * z1 + euler_mascheroni * z2
    return e_max_sr * np.sqrt(variance)


def deflated_sharpe_ratio(observed_sr: float, sr_benchmark: float,
                          n_observations: int, n_trials: int,
                          skewness: float = 0.0, kurtosis: float = 3.0) -> dict:
    """
    Compute the Deflated Sharpe Ratio.
    
    Tests H0: SR* ≤ E[max(SR)] (the strategy is no better than expected by chance)
    
    Args:
        observed_sr: The Sharpe ratio of the selected strategy (annualized)
        sr_benchmark: The benchmark SR (typically 0, or E[max(SR)] from trials)
        n_observations: Number of return observations (e.g., 252 * years for daily)
        n_trials: Number of strategies/parameter combos tested
        skewness: Skewness of returns
        kurtosis: Kurtosis of returns (excess kurtosis + 3, or raw kurtosis)
    
    Returns:
        dict with:
        - dsr_statistic: t-statistic for the deflated test
        - p_value: one-sided p-value (H0: SR ≤ benchmark)
        - is_significant: bool at default α=0.05
        - observed_sr: input
        - expected_max_sr: E[max(SR)] from the trials
        - haircut_pct: percentage reduction from observed to deflated
    
    Implementation:
        1. Compute E[max(SR)] given n_trials
        2. Adjust observed SR for non-normality:
           σ(SR) = sqrt((1 - skew*SR + (kurt-1)/4 * SR^2) / n_observations)
        3. DSR statistic = (observed_SR - E[max(SR)]) / σ(SR)
        4. p-value from normal CDF
    """
    # Expected maximum SR under null
    e_max_sr = expected_max_sharpe(n_trials)
    
    # Standard error of SR (adjusted for non-normality)
    # From Lo (2002) and Bailey & López de Prado (2014)
    sr_std = np.sqrt(
        (1 - skewness * observed_sr + ((kurtosis - 1) / 4) * observed_sr**2)
        / n_observations
    )
    
    # DSR test statistic
    dsr_stat = (observed_sr - e_max_sr) / sr_std if sr_std > 0 else 0.0
    
    # One-sided p-value
    p_value = 1 - stats.norm.cdf(dsr_stat)
    
    return {
        "dsr_statistic": dsr_stat,
        "p_value": p_value,
        "is_significant": p_value < 0.05,
        "observed_sr": observed_sr,
        "expected_max_sr": e_max_sr,
        "haircut_pct": max(0, (1 - e_max_sr / observed_sr) * 100) if observed_sr > 0 else 0,
    }
```

### Probability of Backtest Overfitting: `pbo.py`

PBO (Bailey et al., 2017) measures the probability that the best in-sample strategy will underperform the median out-of-sample:

```python
def compute_pbo(returns_matrix: np.ndarray, n_partitions: int = 16) -> dict:
    """
    Compute Probability of Backtest Overfitting using CSCV.
    
    Algorithm:
    1. Partition the time series into S equal sub-periods (S must be even, ≥ 8)
    2. For each combination C(S, S/2) of sub-periods as in-sample:
       a. Remaining S/2 sub-periods are out-of-sample
       b. Rank all N strategies by IS Sharpe ratio
       c. Select the best IS strategy (rank 1)
       d. Record its OOS rank (out of N strategies)
       e. Compute ω = OOS_rank / N (relative rank, 0 = best, 1 = worst)
    3. PBO = fraction of combinations where ω > 0.5 (best IS performer
       is below median OOS)
    
    Also compute the logit distribution of ω for richer analysis.
    
    Args:
        returns_matrix: shape (T, N) — T timesteps, N strategies
        n_partitions: S — number of time partitions (must be even, default 16)
    
    Returns:
        dict with:
        - pbo: float in [0, 1] — probability of overfitting
        - pbo_distribution: list of ω values per combination
        - logit_distribution: list of logit(ω) values
        - n_combinations: total C(S, S/2) evaluated
        - median_oos_rank: median OOS rank of IS-best strategy
    """
    from itertools import combinations
    
    T, N = returns_matrix.shape
    partition_size = T // n_partitions
    
    # Trim to exact multiple
    returns_trimmed = returns_matrix[:partition_size * n_partitions]
    
    # Split into S partitions
    partitions = np.array_split(returns_trimmed, n_partitions, axis=0)
    
    omega_values = []
    half = n_partitions // 2
    
    for is_indices in combinations(range(n_partitions), half):
        oos_indices = [i for i in range(n_partitions) if i not in is_indices]
        
        # Concatenate IS and OOS partitions
        is_returns = np.concatenate([partitions[i] for i in is_indices], axis=0)
        oos_returns = np.concatenate([partitions[i] for i in oos_indices], axis=0)
        
        # Rank strategies by IS Sharpe
        is_sharpes = _sharpe_ratios(is_returns)  # shape (N,)
        best_is_idx = np.argmax(is_sharpes)
        
        # Rank best IS strategy in OOS
        oos_sharpes = _sharpe_ratios(oos_returns)
        oos_rank = np.sum(oos_sharpes >= oos_sharpes[best_is_idx]) / N
        
        omega_values.append(oos_rank)
    
    pbo = np.mean(np.array(omega_values) > 0.5)
    
    # Logit transform (clip to avoid inf)
    omega_clipped = np.clip(omega_values, 0.01, 0.99)
    logit_vals = np.log(omega_clipped / (1 - omega_clipped))
    
    return {
        "pbo": float(pbo),
        "pbo_distribution": omega_values,
        "logit_distribution": logit_vals.tolist(),
        "n_combinations": len(omega_values),
        "median_oos_rank": float(np.median(omega_values)),
    }


def _sharpe_ratios(returns: np.ndarray, annualization: float = np.sqrt(365)) -> np.ndarray:
    """
    Compute Sharpe ratios for each column.
    Annualize with sqrt(365) for crypto (daily data, 365 trading days).
    """
    mean_r = np.mean(returns, axis=0)
    std_r = np.std(returns, axis=0, ddof=1)
    std_r = np.where(std_r == 0, 1e-10, std_r)  # Avoid division by zero
    return (mean_r / std_r) * annualization
```

**PBO gotchas:**
- `n_partitions` must be even (half goes IS, half goes OOS)
- For S=16: C(16,8) = 12,870 combinations — computationally feasible
- For S=20: C(20,10) = 184,756 — still OK but slower
- Returns matrix needs enough rows: at minimum 16 × 30 = 480 daily observations for 30-day partitions
- PBO is most meaningful with ≥ 20 strategies/param combos (N ≥ 20)

### Automated Gate: `gate.py`

```python
@dataclass
class GateConfig:
    """Configuration for the automated accept/reject gate."""
    pbo_threshold: float = 0.5          # Reject if PBO > threshold
    dsr_alpha: float = 0.05             # DSR significance level
    min_oos_sharpe: float = 0.0         # Minimum OOS Sharpe (optional)
    require_both: bool = True           # Must pass BOTH DSR and PBO (vs. either)


@dataclass
class GateResult:
    """Result of the validation gate."""
    passed: bool
    dsr_result: dict
    pbo_result: dict
    reasons: list[str]                  # Human-readable pass/fail reasons
    confidence: str                     # "high", "medium", "low"


def run_gate(returns_matrix: np.ndarray, selected_strategy_idx: int,
             n_trials: int, config: GateConfig = GateConfig()) -> GateResult:
    """
    Run the full validation gate on a selected strategy.
    
    Steps:
    1. Compute DSR for the selected strategy
    2. Compute PBO on the full returns matrix
    3. Apply thresholds
    4. Generate pass/fail with detailed reasoning
    """
    selected_returns = returns_matrix[:, selected_strategy_idx]
    
    # DSR
    observed_sr = _sharpe_ratios(selected_returns.reshape(-1, 1))[0]
    skew = float(stats.skew(selected_returns))
    kurt = float(stats.kurtosis(selected_returns, fisher=False))
    
    dsr = deflated_sharpe_ratio(
        observed_sr=observed_sr,
        sr_benchmark=0,
        n_observations=len(selected_returns),
        n_trials=n_trials,
        skewness=skew,
        kurtosis=kurt,
    )
    
    # PBO
    pbo = compute_pbo(returns_matrix)
    
    # Gate logic
    reasons = []
    dsr_pass = dsr["is_significant"]
    pbo_pass = pbo["pbo"] <= config.pbo_threshold
    
    if not dsr_pass:
        reasons.append(f"DSR FAIL: p={dsr['p_value']:.4f} > α={config.dsr_alpha}")
    else:
        reasons.append(f"DSR PASS: p={dsr['p_value']:.4f} ≤ α={config.dsr_alpha}")
    
    if not pbo_pass:
        reasons.append(f"PBO FAIL: PBO={pbo['pbo']:.3f} > threshold={config.pbo_threshold}")
    else:
        reasons.append(f"PBO PASS: PBO={pbo['pbo']:.3f} ≤ threshold={config.pbo_threshold}")
    
    if config.require_both:
        passed = dsr_pass and pbo_pass
    else:
        passed = dsr_pass or pbo_pass
    
    return GateResult(
        passed=passed,
        dsr_result=dsr,
        pbo_result=pbo,
        reasons=reasons,
        confidence="high" if (dsr_pass and pbo_pass) else
                   "medium" if (dsr_pass or pbo_pass) else "low",
    )
```

### Combined Report: `validation_report.py`

```python
def generate_validation_report(gate_result: GateResult,
                                walk_forward_result=None) -> dict:
    """
    Generate a comprehensive validation report combining all checks.
    
    Output structure:
    {
        "summary": {
            "verdict": "ACCEPT" or "REJECT",
            "confidence": "high/medium/low",
            "reasons": [...],
        },
        "deflated_sharpe": {
            "observed_sr": float,
            "expected_max_sr": float,
            "dsr_statistic": float,
            "p_value": float,
            "significant": bool,
            "haircut_pct": float,
        },
        "probability_backtest_overfitting": {
            "pbo": float,
            "threshold": float,
            "passed": bool,
            "n_combinations_tested": int,
            "oos_rank_distribution": {...},
        },
        "walk_forward": { ... },  # From s4 if provided
        "metadata": {
            "timestamp": str,
            "n_strategies_tested": int,
            "data_period": str,
            "config": {...},
        }
    }
    """
```

### Test File: `tests/test_statistical_validation.py`

```python
class TestDeflatedSharpe:
    def test_dsr_penalizes_multiple_testing(self):
        """Higher n_trials → lower DSR significance."""
        result_few = deflated_sharpe_ratio(1.5, 0, 252, n_trials=5)
        result_many = deflated_sharpe_ratio(1.5, 0, 252, n_trials=1000)
        assert result_many["p_value"] > result_few["p_value"]

    def test_dsr_known_values(self):
        """Verify against known DSR computation."""
        # SR=2.0, 252 obs, 1 trial, normal returns → should be highly significant
        result = deflated_sharpe_ratio(2.0, 0, 252, n_trials=1)
        assert result["is_significant"]
        assert result["p_value"] < 0.01

    def test_dsr_zero_sharpe_not_significant(self):
        """SR=0 should never be significant."""
        result = deflated_sharpe_ratio(0.0, 0, 252, n_trials=10)
        assert not result["is_significant"]


class TestPBO:
    def test_random_strategies_high_pbo(self):
        """Random strategies should have PBO close to 0.5 or higher."""
        np.random.seed(42)
        random_returns = np.random.randn(500, 50) * 0.01  # 50 random strategies
        result = compute_pbo(random_returns, n_partitions=10)
        assert result["pbo"] > 0.3  # Random should overfit frequently

    def test_trending_strategy_lower_pbo(self):
        """A genuinely trending strategy should have lower PBO."""
        # Create synthetic data where momentum works
        np.random.seed(42)
        prices = np.cumsum(np.random.randn(500) * 0.01 + 0.0005) + 100
        # Create momentum strategy returns that have genuine edge
        # ... (construct carefully)

    def test_pbo_requires_even_partitions(self):
        """Odd n_partitions should raise ValueError."""
        with pytest.raises(ValueError):
            compute_pbo(np.random.randn(100, 10), n_partitions=7)


class TestGate:
    def test_gate_rejects_overfit(self):
        """Strategy with PBO > 0.5 and insignificant DSR is rejected."""
        ...

    def test_gate_accepts_robust(self):
        """Strategy with PBO < 0.5 and significant DSR passes."""
        ...

    def test_full_pipeline_reference_strategy(self):
        """
        End-to-end: dual MA crossover sweep → walk-forward → DSR + PBO gate.
        This is the integration test proving the whole validation stack works.
        """
        ...
```

## Success Criteria

- DSR correctly penalizes for multiple testing: more trials → harder to pass
- PBO correctly identifies random strategies as overfit (PBO ≈ 0.5)
- Automated gate produces clear ACCEPT/REJECT verdicts with reasoning
- Full validation report contains DSR value, PBO value, pass/fail, confidence, and all supporting metrics
- Reference strategy sweep can be run through the complete validation pipeline
- `pytest tests/test_statistical_validation.py` passes

## References

- Decision: `d: two-phase-backtest-workflow`
- Knowledge: Purged K-Fold CV (7+ folds), DSR, PBO, statistical hygiene
- Bailey & López de Prado (2014), "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality" — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551)
- Bailey et al. (2017), "The Probability of Backtest Overfitting" — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253)
- López de Prado (2018), "Advances in Financial Machine Learning", Chapters 11-12
- Lo (2002), "The Statistics of Sharpe Ratios" — standard error of SR derivation
