---
primitive: task
status: open
priority: critical
created: 2026-03-25
owner: belam
depends_on: []
upstream: [quant-baseline-v1]
downstream: [snn-statistical-process-models]
tags: [quant, garch, hawkes, poisson, fractional-differentiation, process-models]
---

# Quant Statistical Process Models

## Research Question
Can advanced statistical process models — GARCH variants, Hawkes processes, fractional differentiation, and Poisson intensity models — provide a stronger feature foundation and direct trading signals than standard technical indicators?

## Scope
Pure statistical/mathematical modeling. No neural networks. This module explores whether the right mathematical framework for the data-generating process unlocks signal that the V1 feature set couldn't find. Applies across ALL asset classes from the other modules.

## Design

### Sub-Module A: GARCH Volatility Modeling

**Models (exhaustive):**
| Model | Captures | Library |
|-------|----------|---------|
| GARCH(1,1) | Baseline volatility clustering | `arch` |
| GJR-GARCH | Leverage effect (down moves → higher vol) | `arch` |
| EGARCH | Asymmetric vol without positivity constraints | `arch` |
| TGARCH | Threshold GARCH — regime-dependent | `arch` |
| FIGARCH | Long memory in volatility (fractionally integrated) | `arch` |
| GARCH-MIDAS | Mixed-frequency (daily vol + monthly macro) | Custom |
| DCC-GARCH | Dynamic conditional correlation between pairs | `rmgarch` (R) or custom |
| Realized GARCH | Uses high-frequency realized vol as measurement | Custom |

**Applied to:** BTC 4h, microcap selection, energy ETFs, stablecoin spreads
**Key outputs:** 
- Standardized residuals (volatility-adjusted returns) as improved features for ML
- Conditional volatility forecasts as standalone trading signals
- Volatility regime classification (high/low/transition)

**Critical:** Returns in PERCENTAGE terms for `arch` library. α + β persistence check.

### Sub-Module B: Hawkes Self-Exciting Processes

**Concept:** Events increase the probability of future events (contagion/clustering).
```
λ(t) = μ + Σ α·exp(-β(t - tᵢ))   for past events tᵢ
```

**Applications:**
- Liquidation cascades in crypto (one large liquidation triggers more)
- Volume spikes (herding behavior)
- Volatility clustering (beyond GARCH — discrete event framework)
- Stablecoin depeg contagion (USDT depeg → DAI depeg)

**Estimation:** Maximum likelihood via `tick` library (Python) or custom EM algorithm
**Features derived:** λ(t) intensity, branching ratio α/β, expected number of events in next window

**Trading signal:** When Hawkes intensity spikes → expect more events → widen stops or reduce position. When intensity decays to baseline μ → safe to re-enter.

### Sub-Module C: Fractional Differentiation

**Problem:** Integer differentiation (returns) achieves stationarity but destroys memory. Price levels have memory but aren't stationary. Fractional order d ∈ (0,1) gives both.

**Method:** 
```python
from fracdiff import Fracdiff
# Find minimum d for ADF stationarity
# Typical: d ≈ 0.1-0.4 preserves >90% correlation with original series
```

**Grid search:** d ∈ [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.75, 1.0]
For each d: ADF test + correlation with original series + ML model performance

**Applied to:** All 7 original features from V1 (log_return already at d=1, but RSI/MACD/ATR at d=0). Find optimal d per feature per asset.

**Hypothesis:** The V1 Lasso zero-feature result used d=1 features. At d=0.2, features retain memory that Lasso might find useful.

### Sub-Module D: Poisson & Compound Poisson Models

**Pure Poisson:** Count of "significant events" per time window
- Define "event" thresholds: returns > 2σ, volume > 3× average, spread deviation > 2σ
- Estimate λ (rate parameter) per regime
- Test for overdispersion → Negative Binomial if variance > mean

**Compound Poisson:** Events arrive as Poisson, but each event has a random magnitude
```
S(t) = Σ_{i=1}^{N(t)} X_i    where N(t) ~ Poisson(λt), X_i ~ Distribution
```
Jump size distributions to test:
- Normal (simple)
- Double exponential (Kou model — different distributions for up/down jumps)
- Power law (fat tails — more realistic for crypto)

**Applied to:** 
- Crypto liquidation events (jump-driven price moves)
- Nuclear policy event arrivals (reactor approvals, regulatory changes)
- Stablecoin depeg events
- Volume spike arrivals

### Sub-Module E: Random Walk Hypothesis Testing

**Formal tests on all assets:**
| Test | Null Hypothesis | What It Tells Us |
|------|----------------|-------------------|
| Augmented Dickey-Fuller | Unit root (random walk) | Stationarity of returns |
| Variance ratio (Lo-MacKinlay) | RW with IID increments | Serial correlation in returns |
| BDS test | IID residuals | Nonlinear dependence after linear filtering |
| Hurst exponent | H=0.5 is random walk | H>0.5 = trending, H<0.5 = mean-reverting |
| Runs test | Random sequence of signs | Sequential dependence |
| Phillips-Perron | Unit root (robust to heteroscedasticity) | Stationarity |

**Per asset:** Run all 6 tests. Assets where RW is rejected → strongest candidates for prediction.
**Per timeframe:** 1h, 4h, daily, weekly — which horizons deviate most from random walk?

**Hurst exponent focus:** 
- H > 0.5 → trending behavior → momentum strategies
- H < 0.5 → mean-reverting → pairs/reversion strategies  
- H ≈ 0.5 → random walk → go home
- Compute rolling H to detect regime changes in trendiness

### Integration: Process Model Features as ML Inputs
Take all outputs from A-E and feed them as features into the standard ML hierarchy:
- GARCH conditional volatility + standardized residuals
- Hawkes intensity λ(t) + branching ratio
- Fractionally differentiated features at optimal d
- Poisson intensity + compound Poisson jump indicator
- Hurst exponent (rolling)
- Variance ratio (rolling)

**This is the "process-aware feature set"** — test whether ML models with these features beat ML models with V1 standard features. The comparison is the key output.

## Acceptance Criteria
- [ ] All GARCH variants calibrated on all assets
- [ ] Hawkes process estimated on event sequences for crypto + nuclear
- [ ] Fractional differentiation grid search with ADF + correlation analysis
- [ ] Poisson/Compound Poisson models on relevant event types
- [ ] Random walk hypothesis tests on all assets at multiple timeframes
- [ ] Process-aware features fed into ML hierarchy
- [ ] Head-to-head: process features vs V1 features vs combined features
- [ ] Per-asset recommendation: which process model framework fits each market?
- [ ] DSR and PBO on any derived trading strategies
- [ ] Results exported + summary report

## Notes
- This module is the mathematical foundation for everything else
- FIGARCH and GARCH-MIDAS may require custom implementation — start with GJR-GARCH
- Hawkes estimation can be unstable for small event counts — need minimum ~50 events
- The fracdiff library handles the heavy lifting for fractional differentiation
- DCC-GARCH for multi-asset correlation dynamics is powerful but computationally heavy
- Rolling Hurst exponent is a direct trading signal (trend/reversion regime)
