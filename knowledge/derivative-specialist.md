---
primitive: knowledge
name: derivative-specialist
description: "Derivatives pricing engineering — volatility surface construction (SVI/SSVI), Greeks computation (AAD, finite differences), stochastic volatility models (Heston, SABR), Monte Carlo pricing (GPU, variance reduction), and GARCH calibration. Use when pricing options, constructing vol surfaces, computing Greeks, calibrating Heston or SABR models, running Monte Carlo simulations, fitting GARCH models, or working with QuantLib. Also use for implied volatility, Black-Scholes extensions, exotic derivatives pricing, or risk-neutral valuation."
tags: [derivatives, pricing, volatility, greeks, monte-carlo]
migrated_from: skills/derivative-specialist
---

# Derivatives Specialist

## Volatility Surface Construction

### SVI Parameterization (Industry Standard)
Raw SVI total implied variance: `w(k) = a + b*(ρ*(k-m) + √((k-m)² + σ²))` where k = log-moneyness.

**Jump-Wings (JW) reparameterization:** Uses ATM variance, ATM skew, min/max slopes, curvature — parameters nearly independent of expiration for longer maturities.

**SSVI (Surface SVI):** Closed-form arbitrage-free surfaces. Reference: `github.com/JackJacquier/SSVI`

### Arbitrage-Free Constraints (Non-Negotiable)
- **Calendar:** Total variance non-decreasing in time
- **Butterfly:** Dupire density non-negative across all strikes
- **Fitting:** Square-root SVI as initial guess → optimize slice-by-slice with penalty for crossing adjacent expiry slices
- **Interpolation:** In total variance space (not implied vol), monotonic splines
- **Weighting:** By vega or reciprocal of bid-ask spread

## Greeks Computation

### Three Approaches
1. **Analytical (closed-form):** ~10K options/sec, limited to vanilla Black-Scholes
2. **Finite differences (bumping):** Δ ≈ [V(S+ε) − V(S−ε)]/(2ε). 2N+1 valuations for N Greeks. Simple but unstable for higher-order Greeks.
3. **AAD (Adjoint Algorithmic Differentiation):** Record forward graph, traverse backward. All first-order Greeks in ≤4× forward cost. O(1) vs O(N) scaling — up to 1,000× faster for large portfolios.

### AAD Implementations
- **QuantLib-Risks** (XAD library)
- **MatLogica AADC** (JIT compiler)
- **JAX** `jax.grad` — GPU-native
- **PyTorch** autograd — 20% overhead for delta+vega (vs 500%+ for finite diff)

Reference: Antoine Savine, "Modern Computational Finance"

## Stochastic Volatility Models

### Heston (Equity Options Standard)

Five parameters: v₀, κ, θ, σ, ρ. Pricing via characteristic function (Carr-Madan FFT or COS method). COS is faster — cosine expansion, vectorizes across strikes and summation terms.

**Critical:** Multiple local minima (κ and σ compensate). Use global search (differential_evolution) + local refinement (Levenberg-Marquardt). Feller condition (2κθ > σ²) often violated — use full truncation for MC. Typical error: 1–5% avg absolute IV error.

### SABR (Interest Rate Standard)
Hagan (2002) approximation: closed-form implied vol as function of (α, β, ρ, ν). β fixed by convention (0, 0.5, or 1). α solved analytically from ATM vol. (ρ, ν) optimized. **Shifted SABR** essential for negative rates. Implementation: `pysabr` on GitHub.

## Monte Carlo Pricing

### Variance Reduction (Essential)
1. **Antithetic variates:** Both Z and −Z → halves variance for monotonic payoffs
2. **Control variates:** Geometric Asian (closed-form) as control → variance × (1−ρ²)
3. **Quasi-random:** Sobol/Halton → O(1/N) vs O(1/√N), ~4× reduction
4. **Path counts:** 100K–1M vanilla Europeans, 1M–10M exotics

### GPU Monte Carlo
Each path = GPU thread. PyTorch pattern:
```python
Z = torch.randn(N_paths, N_steps, device='cuda')
S = S0 * torch.cumprod(torch.exp((r-0.5*σ²)*dt + σ*√dt*Z), dim=1)
# 537× speedup (5M paths, 365 steps: 25ms GPU vs 13,530ms CPU)
# Greeks via autograd — free
```

## GARCH Calibration

Library: `arch` v7.2.0 (Kevin Sheppard)

**Critical trap:** Returns must be in PERCENTAGE terms (1.5 for 1.5%), not decimal. Affects convergence dramatically. Use GJR-GARCH for equities (leverage effect dominates). Multiple starting points essential. α + β typically 0.98–0.99 for daily equities. AIC/BIC for model selection.

---

## Calibration Patterns

### Heston Calibration

```python
from scipy.optimize import differential_evolution, minimize

def heston_objective(params, market_vols, strikes, expiries):
    v0, kappa, theta, sigma, rho = params
    model_vols = [heston_price_cos(S, K, T, r, v0, kappa, theta, sigma, rho)
                  for K, T in zip(strikes, expiries)]
    return np.sum((np.array(model_vols) - market_vols)**2)

# Parameter bounds
bounds = [
    (0.01, 1.0),   # v0: initial variance
    (0.01, 10.0),  # κ: mean-reversion speed
    (0.01, 1.0),   # θ: long-run variance
    (0.1, 5.0),    # σ: vol-of-vol
    (-0.95, -0.1)  # ρ: correlation (typically negative for equities)
]

# Step 1: Global search (CRITICAL — multiple local minima)
result = differential_evolution(heston_objective, bounds,
                                args=(market_vols, strikes, expiries),
                                maxiter=1000, seed=42)

# Step 2: Local refinement
result = minimize(heston_objective, result.x,
                  args=(market_vols, strikes, expiries),
                  method='L-BFGS-B', bounds=bounds)

# Feller condition check
v0, kappa, theta, sigma, rho = result.x
feller = 2 * kappa * theta > sigma**2
if not feller:
    print("WARNING: Feller condition violated — use full truncation for MC")
```

### COS Method (Fang-Oosterlee)

Faster than Carr-Madan FFT. Uses cosine expansion and vectorizes across both strikes and summation terms. Key for production calibration speed.

```python
def heston_cos_price(S, K, T, r, v0, kappa, theta, sigma, rho, N=256):
    """COS method for Heston model pricing.
    N: number of cosine expansion terms (256 typically sufficient)
    Vectorize across K for efficiency."""
    # Characteristic function of log-price under Heston
    # ... (standard Heston CF implementation)
    # Cosine expansion coefficients
    # ... (Fang-Oosterlee 2008)
    pass
```

### SABR Calibration

```python
import pysabr

# β fixed by market convention
beta = 0.5  # or 0, 1

# α solved analytically from ATM vol
# (ρ, ν) optimized
sabr = pysabr.Hagan2002(f=forward, shift=0.03, t=expiry,
                         v_atm=atm_vol, beta=beta)
alpha, rho, volvol = sabr.fit(strikes, market_vols)

# For negative rates: shifted SABR (F → F + shift)
```

### SVI Surface Fitting

```python
def svi_total_variance(k, a, b, rho, m, sigma):
    """Raw SVI parameterization.
    k: log-moneyness (ln(K/F))
    Returns: total implied variance w(k)
    """
    return a + b * (rho * (k - m) + np.sqrt((k - m)**2 + sigma**2))

# Fitting procedure:
# 1. Square-root SVI as initial guess
# 2. Optimize slice-by-slice
# 3. Penalty terms for crossing adjacent expiry slices
# 4. Weight by vega or 1/bid-ask-spread
# 5. Interpolate in total variance space with monotonic splines
# 6. Verify: total variance non-decreasing (calendar), Dupire density ≥ 0 (butterfly)
```

### GARCH Calibration

```python
from arch import arch_model

# CRITICAL: percentage returns, not decimal
returns_pct = log_returns * 100

# Plain GARCH(1,1)
garch = arch_model(returns_pct, vol='Garch', p=1, q=1)
result = garch.fit(disp='off')

# GJR-GARCH (preferred for equities — captures leverage effect)
gjr = arch_model(returns_pct, vol='GJR-GARCH', p=1, o=1, q=1)
result_gjr = gjr.fit(disp='off')

# Model selection
print(f"GARCH AIC: {result.aic}, GJR-GARCH AIC: {result_gjr.aic}")

# Persistence check
alpha_beta = result.params['alpha[1]'] + result.params['beta[1]']
print(f"α + β = {alpha_beta:.4f}")  # Should be 0.98–0.99 for daily equities
```


---

# Calibration Patterns

## Heston Calibration

```python
from scipy.optimize import differential_evolution, minimize

def heston_objective(params, market_vols, strikes, expiries):
    v0, kappa, theta, sigma, rho = params
    model_vols = [heston_price_cos(S, K, T, r, v0, kappa, theta, sigma, rho)
                  for K, T in zip(strikes, expiries)]
    return np.sum((np.array(model_vols) - market_vols)**2)

# Parameter bounds
bounds = [
    (0.01, 1.0),   # v0: initial variance
    (0.01, 10.0),  # κ: mean-reversion speed
    (0.01, 1.0),   # θ: long-run variance
    (0.1, 5.0),    # σ: vol-of-vol
    (-0.95, -0.1)  # ρ: correlation (typically negative for equities)
]

# Step 1: Global search (CRITICAL — multiple local minima)
result = differential_evolution(heston_objective, bounds,
                                args=(market_vols, strikes, expiries),
                                maxiter=1000, seed=42)

# Step 2: Local refinement
result = minimize(heston_objective, result.x,
                  args=(market_vols, strikes, expiries),
                  method='L-BFGS-B', bounds=bounds)

# Feller condition check
v0, kappa, theta, sigma, rho = result.x
feller = 2 * kappa * theta > sigma**2
if not feller:
    print("WARNING: Feller condition violated — use full truncation for MC")
```

## COS Method (Fang-Oosterlee)

Faster than Carr-Madan FFT. Uses cosine expansion and vectorizes across both strikes and summation terms. Key for production calibration speed.

```python
def heston_cos_price(S, K, T, r, v0, kappa, theta, sigma, rho, N=256):
    """COS method for Heston model pricing.
    N: number of cosine expansion terms (256 typically sufficient)
    Vectorize across K for efficiency."""
    # Characteristic function of log-price under Heston
    # ... (standard Heston CF implementation)
    # Cosine expansion coefficients
    # ... (Fang-Oosterlee 2008)
    pass
```

## SABR Calibration

```python
import pysabr

# β fixed by market convention
beta = 0.5  # or 0, 1

# α solved analytically from ATM vol
# (ρ, ν) optimized
sabr = pysabr.Hagan2002(f=forward, shift=0.03, t=expiry,
                         v_atm=atm_vol, beta=beta)
alpha, rho, volvol = sabr.fit(strikes, market_vols)

# For negative rates: shifted SABR (F → F + shift)
```

## SVI Surface Fitting

```python
def svi_total_variance(k, a, b, rho, m, sigma):
    """Raw SVI parameterization.
    k: log-moneyness (ln(K/F))
    Returns: total implied variance w(k)
    """
    return a + b * (rho * (k - m) + np.sqrt((k - m)**2 + sigma**2))

# Fitting procedure:
# 1. Square-root SVI as initial guess
# 2. Optimize slice-by-slice
# 3. Penalty terms for crossing adjacent expiry slices
# 4. Weight by vega or 1/bid-ask-spread
# 5. Interpolate in total variance space with monotonic splines
# 6. Verify: total variance non-decreasing (calendar), Dupire density ≥ 0 (butterfly)
```

## GARCH Calibration

```python
from arch import arch_model

# CRITICAL: percentage returns, not decimal
returns_pct = log_returns * 100

# Plain GARCH(1,1)
garch = arch_model(returns_pct, vol='Garch', p=1, q=1)
result = garch.fit(disp='off')

# GJR-GARCH (preferred for equities — captures leverage effect)
gjr = arch_model(returns_pct, vol='GJR-GARCH', p=1, o=1, q=1)
result_gjr = gjr.fit(disp='off')

# Model selection
print(f"GARCH AIC: {result.aic}, GJR-GARCH AIC: {result_gjr.aic}")

# Persistence check
alpha_beta = result.params['alpha[1]'] + result.params['beta[1]']
print(f"α + β = {alpha_beta:.4f}")  # Should be 0.98–0.99 for daily equities
```
