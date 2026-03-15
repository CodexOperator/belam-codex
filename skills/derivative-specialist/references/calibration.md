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
