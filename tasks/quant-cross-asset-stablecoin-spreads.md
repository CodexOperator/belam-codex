---
primitive: task
status: open
priority: critical
created: 2026-03-25
owner: belam
depends_on: []
upstream: [quant-baseline-v1]
downstream: [snn-cross-asset-stablecoin-spreads]
tags: [quant, cross-asset, stablecoin, arbitrage, spreads]
pipeline_template: 
current_stage: 
pipeline_status: 
launch_mode: queued
---
# Quant Cross-Asset & Stablecoin Spread Models

## Research Question
Can quant models detect and predict spread dynamics between correlated crypto assets, stablecoins, and cross-exchange listings — finding arbitrage and mean-reversion opportunities in less-studied feature space?

## Scope
Pure quant signal analysis on spread/basis dynamics. Three sub-modules:

### Sub-Module A: Stablecoin Basis Trades
**Pairs:** USDT/USDC, USDT/DAI, USDC/DAI, USDT/BUSD (where available)
**Data:** 1h candles from Binance/Kraken via ccxt (stablecoin pairs have tighter timeframes)
**Target:** Spread deviation from par (should be ≈ 0). Predict direction and magnitude of mean-reversion.

**Features:**
- Spread level (current deviation from 1.0000)
- Spread velocity (1h, 4h, 24h rolling change)
- DeFi yield differentials (Aave/Compound lending rates — proxy for capital flow incentive)
- On-chain flow: net USDT minting/burning events (Tether treasury activity)
- Aggregate DEX volume ratio (USDT vs USDC swap volumes)
- Gas fees / Solana priority fees (affects arbitrageur cost basis)
- BTC volatility (VIX-proxy: stablecoins depeg more during crypto crashes)

**Models:** Full hierarchy (Linear → XGBoost → MLP). Emphasis on regime detection — when does a stablecoin spread reflect transient noise vs structural stress?

**Poisson component:** Depeg events are rare (Poisson-distributed). Model the intensity λ(t) as a function of observable features. When λ spikes, the spread model should widen its prediction intervals.

### Sub-Module B: Cross-Exchange Spread
**Pairs:** BTC Binance vs BTC Coinbase, ETH Binance vs ETH Kraken, SOL Binance vs SOL Coinbase
**Data:** 1h and 4h candles, synchronized by timestamp
**Target:** Spread dynamics — predict which direction convergence goes and how fast

**Features:**
- Spread level and velocity
- Volume imbalance (Binance volume / Coinbase volume)
- Funding rate differential (Binance perpetuals vs Coinbase perpetuals)
- BTC dominance index change
- Aggregate market volatility (rolling ATR of BTC)
- Hour-of-day / day-of-week seasonality (settlement times, timezone effects)

**Models:** Full hierarchy + Ornstein-Uhlenbeck parameter estimation (θ, μ, σ for the spread)

### Sub-Module C: Crypto Correlation Regime
**Pairs:** BTC/ETH, BTC/SOL, ETH/SOL, BTC/AVAX
**Data:** 4h candles
**Target:** Predict correlation regime transitions. When BTC/ETH decorrelate, which one snaps back?

**Features:**
- Rolling correlation (20, 50, 100 candle windows)
- Correlation velocity (derivative of rolling correlation)
- Relative strength (ratio of cumulative returns over window)
- Volume ratio changes
- RSI divergence (RSI_BTC - RSI_ETH)
- MACD divergence between pairs

**Models:** Full hierarchy. Classification target: {BTC_reverts, ETH_reverts, spread_widens, neither}

### Prediction Horizons
| Horizon | Best For |
|---------|----------|
| 1h | Stablecoin basis (fast mean-reversion) |
| 4h | Cross-exchange spread |
| 1-3 days (6-18 candles of 4h) | Correlation regime transitions |

### Evaluation
- All standard metrics (MAE, R², directional accuracy, Sharpe)
- Mean-reversion specific: half-life estimation, hit rate on reversion predictions
- DSR and PBO for all strategies
- Transaction cost sensitivity: how much alpha survives at 10bps, 20bps, 50bps costs?
- Drawdown analysis: maximum drawdown on spread trades

## Acceptance Criteria
- [ ] All three sub-modules (stablecoin, cross-exchange, correlation) fully implemented
- [ ] OU parameter estimation on all spread series
- [ ] Poisson intensity model for stablecoin depeg events
- [ ] Per-pair diagnostic: which spreads have tradeable structure?
- [ ] Transaction cost sensitivity analysis
- [ ] DSR and PBO for all strategies
- [ ] Results exported + summary report

## Notes
- Stablecoin data may have less history on some pairs — document availability per pair
- Cross-exchange time synchronization is critical — align on UTC hour boundaries
- DeFi yield data (Aave/Compound rates) available via DeFi Llama API or The Graph
- This is the most directly actionable module for actual arbitrage trading
