---
primitive: knowledge
name: predictionmarket-specialist
description: "Prediction market mechanics and market microstructure — LMSR cost functions, Polymarket architecture, market impact models, algorithmic market making (Avellaneda-Stoikov), VPIN adverse selection, optimal execution (Almgren-Chriss), and combinatorial prediction markets. Use when working with prediction markets (Polymarket, Kalshi, Metaculus), implementing automated market makers, analyzing market impact, building market-making strategies, or understanding order execution optimization. Also use for CLOB mechanics, conditional tokens, softmax-as-pricing, or information-theoretic market design."
tags: [prediction-markets, microstructure, market-making, lmsr, execution]
migrated_from: skills/predictionmarket-specialist
---

# Prediction Market Specialist

## LMSR: The Mathematical Foundation

The Logarithmic Market Scoring Rule cost function is **softmax in disguise**:

**Cost function:** `C(q) = b · ln(Σ exp(qᵢ/b))` — this is scaled LogSumExp

**Marginal price:** `∂C/∂qᵢ = exp(qᵢ/b) / Σⱼ exp(qⱼ/b)` — this is exactly softmax with temperature b

**Binary market price:** Simplifies to sigmoid: `p₁ = 1/(1 + exp(-(q₁-q₂)/b))`

### Liquidity Parameter b
Controls three properties simultaneously:
- **Maximum loss:** Bounded by `b·ln(n)` for n outcomes
- **Depth:** Capital needed to move prices
- **Sensitivity:** Response to new information

Small b = twitchy (thin markets). Large b = sticky (thick markets).

**Setting b:** Given risk budget F, set `b = F/ln(n)` to ensure market maker can always cover payouts.

### Numerical Stability (Critical)
```python
# Log-sum-exp trick — MUST USE or overflow at q/b > ~700
c = max(q_i / b for all i)
cost = b * (c + math.log(sum(math.exp(q_i/b - c) for q_i in q)))
```

### Information Theory Connection
- LMSR ≡ logarithmic scoring rule (strictly proper → incentivizes truthful reporting)
- Convex conjugate of LogSumExp = negative entropy → LMSR = maximum entropy inference
- Initialization (all q equal) → uniform distribution
- Chen & Vaughan (2010): Hanson market makers ≡ regularized online follow-the-leader (b = regularization strength)

## Polymarket Architecture

### Three Layers
1. **Conditional Token Framework (CTF):** Gnosis ERC-1155 tokens. Up to 256 outcomes per event. Binary: 1 USDC → 1 YES + 1 NO (invariant: YES + NO = $1).
2. **Hybrid CLOB:** Off-chain matching for speed, on-chain settlement for trustlessness. Orders are EIP-712 signed structured data.
3. **UMA Optimistic Oracle:** Propose result (post ~$750 USDC bond) → 2h dispute window → if no dispute, accepted; if disputed, UMA token holders vote.

### CTFExchange Execution Modes
- **Direct match:** User-to-user, no minting
- **Minting:** New shares created when opposite-outcome orders match in price
- **Merging:** Shares burned when opposite sell orders meet

Volume: >$1.37B through September 2024.

## Market Microstructure

### Square-Root Market Impact (Universal Law)
```
I(Q) ≈ Y · σ · √(Q/V)
```
- Q = metaorder size, V = daily volume, σ = daily volatility, Y ≈ 1
- Holds across equities, futures, options, crypto
- Impact exponent δ ≈ 1/2 confirmed by Sato & Kanazawa (2024) on TSE data
- After completion: ~2/3 of peak impact remains permanently

### Almgren-Chriss Optimal Execution
Closed-form trajectory: `xₖ = X · sinh(κ(T-tₖ)) / sinh(κT)`
- κ = √(λσ²/η) — urgency parameter
- λ → 0 (risk-neutral): converges to TWAP
- λ → ∞ (risk-averse): immediate liquidation
- Each λ traces a point on the efficient frontier (expected cost vs variance)

### Avellaneda-Stoikov Market Making
- **Reservation price:** `r(t) = s(t) - q·γ·σ²·(T-t)` — adjusts mid by inventory
- **Optimal spread:** `δ* = γσ²(T-t) + (2/γ)·ln(1 + γ/κ)` — balances inventory risk vs order arrival
- **Order arrival:** `λ(δ) = A·exp(-κδ)` — exponential decay with distance from mid
- **Implementation:** Hummingbot (open-source, full A-S model)

### VPIN (Adverse Selection Detector)
1. Divide trades into fixed-**volume** buckets (not time)
2. Classify volume as buy/sell using price changes
3. VPIN = rolling avg of |V_buy − V_sell| / V_total
4. **VPIN > 0.7 → danger** — heavily one-sided flow, widen quotes
5. Detected 2010 Flash Crash >1 hour before impact

## Combinatorial Prediction Markets

Bets on outcome combinations (e.g., "same party wins Ohio AND Pennsylvania") face #P-hard pricing (Chen, Fortnow et al., 2008).

### Practical Approaches
- **Bayesian network factorization:** Polynomial time for tree-structured conditional independence
- **Constraint generation:** Convex optimization
- **Independent treatment + arbitrage:** Industry standard — treat related securities independently, let cross-market arbitrage maintain consistency
- **Bounded VC dimension:** Enables sublinear-time algorithms (arXiv 2411.08972, 2024)
