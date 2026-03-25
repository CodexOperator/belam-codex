---
primitive: task
status: open
priority: critical
created: 2026-03-25
owner: belam
depends_on: []
upstream: [quant-baseline-v1]
downstream: [snn-microcap-crypto-baseline]
tags: [quant, crypto, microcap, baseline, swing-trading]
---

# Quant Microcap Crypto Baseline

## Research Question
Do standard and exotic quant models extract tradeable signal from microcap crypto tokens — assets with thinner orderbooks, less algorithmic coverage, and more dramatic regime shifts than BTC?

## Scope
Pure quant signal analysis. NO SNN/neural-temporal models — those belong in the paired SNN task. This notebook tests: Linear → Ridge → Lasso → Random Forest → XGBoost → LightGBM → MLP.

## Design

### Assets
- **BTC/USDT 4h** (reference — rerun from V1 but with expanded horizon + features)
- **5-10 microcap tokens** selected by Shael, including:
  - Binance-listed microcaps (via ccxt)
  - **Solana DEX tokens** (Jupiter/Raydium) via Birdeye API or Bitquery V2 GraphQL
  - Mix of established microcaps (6+ months data) and newer tokens (2-3 months)

### Data Pipeline
- **CEX tokens:** ccxt (Binance, KuCoin) — 4h candles, paginate for full history
- **Solana DEX tokens:** Birdeye API (OHLCV endpoint, 1000 records/call, paginate), cache to CSV
- **Data quality gates:** Minimum 500 candles after warmup. Reject tokens with >5% gap rate or zero-volume stretches >24h.

### Feature Engineering (Expanded from V1)

**Standard features (7 from V1):**
log_return, range, log_volume, RSI(14), MACD_hist, ATR_ratio, SMA_dev

**Moving average crosses (new):**
- SMA(50) vs SMA(200) — golden/death cross binary + distance metric
- EMA(12) vs EMA(26) — faster cross signal
- SMA(20) vs SMA(50) — intermediate swing signal
- Cross recency: candles since last cross event (captures "just crossed" momentum)

**Exotic features (new, where available):**
- Orderbook depth asymmetry (top 10 levels bid/ask ratio) — Binance WebSocket L2
- Funding rate (perpetual futures, Binance) — BTC and larger microcaps only
- Open interest delta (Binance futures)
- Volume profile: volume-weighted average price deviation (VWAP_dev)
- Liquidity score: rolling average spread as % of price

**Microcap-specific features:**
- Holder concentration (Solana: top 10 wallet % via Birdeye)
- DEX volume vs CEX volume ratio (for dual-listed tokens)
- Whale transaction count (transfers > $50K)

### Prediction Horizons (Multi-horizon)
All models trained separately for each horizon:

| Horizon | Target | Formulation | Use Case |
|---------|--------|-------------|----------|
| 1 candle (4h) | next-candle return | Regression | Day trading reference |
| 5 candles (20h) | 5-candle cumulative return | Regression | Short swing |
| 10 candles (40h) | 10-candle cumulative return | Regression | Medium swing |
| 10 candles | P(close[t+10] > close[t]) | Binary classification (calibrated) | Swing probability |
| 20 candles (80h) | 20-candle cumulative return | Regression | Multi-day swing |

### Walk-Forward Validation
- 3 folds expanding window (same as V1)
- **Purge gap = max(prediction_horizon, 20 candles)** — critical for multi-horizon targets
- For shorter-history tokens (< 2000 candles): 2 folds with 60/40 and 80/20 splits
- Pool test predictions across folds for primary metrics

### Model Grid (Exhaustive)
Every model × every feature set × every horizon × every asset:

| Model | Hyperparameter Search |
|-------|----------------------|
| Linear | No params |
| Ridge | α ∈ [0.001, 0.01, 0.1, 1.0, 10.0, 100.0] |
| Lasso | α ∈ [0.0001, 0.001, 0.01, 0.1, 1.0] |
| ElasticNet | α × l1_ratio grid |
| Random Forest | n_estimators ∈ [100, 200, 500], max_depth ∈ [5, 10, 15, None] |
| XGBoost | depth × lr × subsample grid |
| LightGBM | Same grid as XGBoost |
| CatBoost | Include for comparison (handles categoricals natively) |
| MLP | hidden ∈ [(64,32), (128,64), (256,128,64)], dropout ∈ [0.1, 0.2, 0.3] |

### Evaluation Metrics
- MAE, RMSE, R², Pearson correlation (regression targets)
- Directional accuracy, calibrated probability accuracy (classification target)
- Sharpe ratio with transaction costs (0.1% CEX, 0.3% DEX — Solana swap fees are higher)
- Deflated Sharpe Ratio (correct for selection bias across all experiments)
- PBO (Probability of Backtest Overfitting) — reject if > 0.5
- Cumulative PnL curves with buy-and-hold benchmark
- Per-regime performance: high-vol vs low-vol (ATR-based split)

### Statistical Hygiene
- Purged K-fold with proper embargo
- Fractional differentiation (fracdiff) as alternative to raw returns — test d ∈ [0.1, 0.2, 0.3, 0.4]
- GJR-GARCH residuals as volatility-adjusted returns
- Bootstrap CI on all headline metrics
- Bonferroni correction for multiple comparisons across the full grid

## Acceptance Criteria
- [ ] Data pipeline working for both CEX (ccxt) and DEX (Birdeye/Bitquery) tokens
- [ ] All model × feature × horizon combinations run with pooled walk-forward metrics
- [ ] Lasso feature survival analysis per asset per horizon (which features survive at each horizon?)
- [ ] Moving average cross features tested as additive block
- [ ] Multi-horizon comparison: does 5-10 candle horizon unlock signal that 1-candle couldn't find?
- [ ] Per-asset diagnostic: which microcaps have exploitable structure vs which are pure noise?
- [ ] DSR and PBO computed for all strategies
- [ ] Feature importance comparison across models and assets
- [ ] Results exported to CSV + summary report

## Notes
- Swing trading focus: the 5-20 candle horizons are the primary research output
- Golden/death cross features may be strongest on BTC and larger microcaps — test per-asset
- Solana DEX tokens will have shorter history — adjust fold structure accordingly
- Shael to provide specific token list (microcap picks)
- This task produces QUANT-ONLY results. SNN experiments use these results as baseline reference.
