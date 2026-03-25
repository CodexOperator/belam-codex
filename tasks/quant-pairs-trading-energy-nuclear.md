---
primitive: task
status: open
priority: critical
created: 2026-03-25
owner: belam
depends_on: []
upstream: []
downstream: [snn-pairs-trading-energy-nuclear]
tags: [quant, pairs-trading, energy, nuclear, ornstein-uhlenbeck, poisson]
---

# Quant Pairs Trading: Energy & Nuclear Indices

## Research Question
Do energy and nuclear index pairs exhibit statistically significant mean-reverting spread dynamics that can be modeled with Ornstein-Uhlenbeck processes enhanced by Poisson jump detection?

## Scope
Classical statistical pairs trading with modern quant methods. No neural models — those belong in the SNN paired task. This is OU estimation, cointegration testing, jump-diffusion modeling, and quant ML on spread features.

## Design

### Asset Pairs (Priority Order)

**Nuclear Pair (Primary):**
| ETF | Ticker | Description | AUM |
|-----|--------|-------------|-----|
| Global X Uranium ETF | URA | Broad uranium mining | ~$2.6B |
| VanEck Uranium+Nuclear Energy | NLR | Nuclear utilities + miners | ~$900M |
| Sprott Uranium Miners ETF | URNM | Pure uranium miners | ~$1.5B |
| Range Nuclear Renaissance Index ETF | NUKZ | Next-gen nuclear | ~$200M |

**Pairs to test:** URA/NLR, URA/URNM, URNM/NLR, URNM/NUKZ, CCJ/DNN (individual miners)

**Energy Cross-Sector:**
| Pair | Tickers | Dynamic |
|------|---------|---------|
| Nuclear vs Natural Gas | NLR vs UNG | Substitution/competition |
| Nuclear vs Clean Energy | NLR vs ICLN | Policy correlation |
| Uranium vs Oil | URA vs USO | Commodity cycle divergence |
| Clean vs Fossil | ICLN vs XLE | Energy transition trade |

**Data:** yfinance daily candles, 3-10 years depending on ETF inception date.

### Statistical Framework

#### Step 1: Cointegration Testing
- Engle-Granger two-step test
- Johansen trace and maximum eigenvalue tests
- Phillips-Ouliaris test
- **Only proceed with pairs that show cointegration at p < 0.05**

#### Step 2: Ornstein-Uhlenbeck Parameter Estimation
For cointegrated spread S(t):
```
dS = θ(μ - S)dt + σdW
```
Estimate via:
- Maximum Likelihood (exact discretization)
- OLS on ΔS = a + b·S_{t-1} (quick estimate: θ = -b/Δt, μ = -a/b)
- Bayesian estimation with informative priors (useful for short time series)

Key parameters:
- **θ (mean-reversion speed):** Higher = faster reversion = more trades/year
- **μ (equilibrium level):** May drift — use rolling μ estimation
- **σ (noise):** Determines entry/exit thresholds
- **Half-life:** ln(2)/θ — number of days to revert halfway

#### Step 3: Jump-Diffusion Extension
```
dS = θ(μ - S)dt + σdW + J·dN(λ)
```
N(λ) = Poisson process with intensity λ (jumps per unit time)
J ~ N(μ_J, σ_J) = jump size distribution

**Jump detection:** 
- Barndorff-Nielsen & Shephard bipower variation test
- Lee & Mykland jump test (identifies specific jump times)
- Regime: jump intensity λ(t) as function of VIX, policy news, uranium spot price changes

**Why Poisson matters for nuclear pairs:**
Nuclear sector is driven by discrete events — reactor approvals, policy announcements, accidents, uranium supply disruptions. These arrive as Poisson-distributed jumps that break the OU mean-reversion temporarily. Detecting "this is a jump, not a reversion opportunity" prevents catastrophic trades.

#### Step 4: Feature Engineering on Spreads

| Feature | Description |
|---------|-------------|
| Spread Z-score | (S - μ_rolling) / σ_rolling |
| Spread velocity | ΔS / Δt |
| Spread acceleration | Δ²S / Δt² |
| Half-life estimate | Rolling OU θ estimation |
| Jump intensity | Rolling Poisson λ from recent jumps |
| VIX level | Market fear gauge |
| Uranium spot price Δ | Commodity driver |
| 10Y yield Δ | Rate sensitivity (nuclear = capital intensive) |
| Policy sentiment | Nuclear policy news proxy (e.g., NLP on news API) |

#### Step 5: Quant Model Hierarchy on Spread Features
Full hierarchy (Linear → XGBoost → MLP) predicting:
- Next-day spread return (regression)
- Spread direction over next 5 days (classification)
- Probability of spread crossing zero within 10 days (classification)
- Optimal entry: is current Z-score > 2σ AND reversion probability > 60%?

### Trading Strategy Backtest
- **Entry:** Spread Z-score > entry_threshold (test 1.5, 2.0, 2.5σ)
- **Exit:** Spread reverts to exit_threshold (test 0.0, 0.5σ)
- **Stop-loss:** Spread reaches stop_threshold (test 3.0, 4.0σ) — prevents holding through regime breaks
- **Position sizing:** Kelly criterion based on model's predicted win rate and payoff ratio
- **Transaction costs:** 5-10 bps per leg (ETF trading)

### Evaluation
- Sharpe ratio (annualized, after costs)
- Maximum drawdown and Calmar ratio
- Win rate and average win/loss ratio
- Number of trades per year (capacity)
- DSR and PBO (mandatory)
- Comparison: OU-based strategy vs ML-enhanced strategy vs simple Z-score mean-reversion
- Out-of-sample: last 20% of data held as pure OOS test (not part of walk-forward)

## Acceptance Criteria
- [ ] Cointegration tests on all pairs — only proceed with significant pairs
- [ ] OU parameter estimation (MLE + OLS + Bayesian) on all cointegrated pairs
- [ ] Jump detection (BN-S bipower variation + Lee-Mykland) on all pairs
- [ ] Jump-diffusion model calibrated
- [ ] Full ML hierarchy on spread features
- [ ] Trading strategy backtest with transaction costs
- [ ] DSR and PBO on all strategies
- [ ] Per-pair diagnostic: which pairs have tradeable half-lives?
- [ ] Results exported + summary report

## Notes
- Nuclear ETF history varies: URA since 2010, NUKZ since 2023, URNM since 2019
- CCJ and DNN (Cameco and Denison Mines) have longest individual history
- Uranium spot price available via Numerco or UxC (may need proxy: URA NAV premium/discount)
- Jump-diffusion is the intellectually novel component — this isn't standard pairs trading
- Half-lives < 5 days are aggressive (high frequency for ETF pairs); 10-30 days is the sweet spot
