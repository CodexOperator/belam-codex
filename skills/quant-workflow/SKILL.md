---
name: quant-workflow
description: Quant research workflow — research-to-production pipeline, statistical hygiene (overfitting prevention), feature engineering, model selection, and the daily workflow of quant researchers at top firms. Use when designing research pipelines, validating backtest results, checking for overfitting, engineering features for financial ML, selecting ML models for quant finance, or understanding production quant workflows. Also use for Deflated Sharpe Ratio, purged cross-validation, fractional differentiation, or walk-forward validation.
---

# Quant Research Workflow

## Research-to-Production Pipeline

Five stage gates, steep funnel (~28 tested → ~3 survive):

1. **Idea generation** — post-trade analysis, academic literature, cross-asset meetings, LLM alpha mining (RD-Agent, Alpha-GPT)
2. **Signal development** — feature engineering, model training, initial validation
3. **Backtesting** — realistic transaction costs, slippage, spread. Must include DSR and PBO checks. QuantConnect processes 15K+ backtests/day.
4. **Paper trading** — live data, no real capital. Weeks to months depending on frequency.
5. **Live capital allocation** — gradual ramp-up, continuous risk overlay (position limits, drawdown stops, kill-switches, factor exposure frameworks)

## Statistical Hygiene (Non-Optional)

### Purged K-Fold Cross-Validation
Remove from training any observation whose label overlaps in time with test labels. Apply embargo excluding observations immediately after each test fold.

```python
from skfolio.model_selection import CombinatorialPurgedCV
cv = CombinatorialPurgedCV(n_splits=10, n_test_splits=2, purge_gap=5)
```

**Minimum 7 folds for Sharpe claims.** Bootstrap CI for F1 lift claims.

### Deflated Sharpe Ratio (DSR)
Corrects for selection bias AND non-normal returns. A Sharpe of 2.0 from the best of 1,000 trials is likely noise. The deflated benchmark SR₀ accounts for expected maximum Sharpe among N trials under null.

### Probability of Backtest Overfitting (PBO)
Partition backtest into S sub-periods. Measure fraction of IS/OOS splits where IS-optimal underperforms OOS. **PBO > 0.5 = likely overfitting. Reject.**

### Fractional Differentiation
Integer differentiation (returns) achieves stationarity but destroys memory. Use fractional order d ∈ (0,1):

```python
from fracdiff import Fracdiff
# Find minimum d for ADF stationarity — typically d ≈ 0.1–0.4
# Preserves >90% correlation with original series
```

## Feature Engineering Principles

- **Fractional differentiation** over integer returns when memory matters
- **GARCH residuals** as volatility-adjusted returns (use `arch` v7.2.0, returns in PERCENTAGE terms)
- **GJR-GARCH** dominates plain GARCH(1,1) for equities (leverage effect)
- α + β typically 0.98–0.99 for daily equity returns (extreme persistence)

## ML Model Selection (Production Evidence)

### Works Now
| Model | Use Case | Evidence |
|-------|----------|---------|
| XGBoost/LightGBM | Mid-frequency tabular alpha | Production workhorse, beats deep learning on tabular |
| LSTM/GRU | Order-book short-horizon | Proven at multiple firms |
| Neural surrogates | Derivatives pricing | Millisecond recalibration, deployed |
| Deep RL hedging | Cost-aware hedging policies | Deployed on derivatives desks |
| LLM sentiment | Earnings call analysis | 247 bps annualized (S&P Global) |

### Promising but Fragile
| Model | Issue |
|-------|-------|
| Transformers (financial) | Degrade in volatile regimes, need continuous recalibration |
| PatchTST | 21% MSE reduction but non-stationarity untested |
| TimesFM (200M params) | Zero-shot rivaling supervised; tail event generalization unknown |
| Mamba / state-space | Linear complexity good; Graph-Mamba hybrids unproven |

### Hype — Push Back
- End-to-end autonomous AI trading agents
- Quantum ML for trading
- Foundation models as standalone predictors
- LLMs for direct signal generation

## Daily Quant Researcher Workflow

**Time allocation:** 60% coding, 30% analysis, 10% meetings

**Typical day (Citadel Securities):**
- 8:30am: Check overnight P&L and compute jobs
- Morning: Collaborate with global colleagues, refine systematic strategies
- Afternoon: Post-trade analysis, cross-asset meetings, strategy refinement
- ~6pm: Leave. Average 47.8h/week, 63% remote 3+ days.

**Tools:** Python (NumPy, Pandas/Polars, scikit-learn, PyTorch), C++/Rust for latency-sensitive, Jupyter, Bloomberg terminals, AI coding assistants.

**Key quotes:**
- "95% of the time, our strategies don't require human input: they're fully systematic." — Citadel Securities
- "Things that would have taken 10-15 minutes now take seconds." — Balyasny
- "If you're writing code from scratch, I don't know what you're doing." — Verition
- "Single-person teams now compete effectively using AI helpers." — Igor Tulchinsky, WorldQuant
