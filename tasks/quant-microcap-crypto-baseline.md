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
pipeline_template: 
current_stage: 
pipeline_status: 
launch_mode: queued
---
# Quant Microcap Crypto Baseline

## Research Question
Do standard and exotic quant models extract tradeable signal from microcap crypto tokens — assets with thinner orderbooks, less algorithmic coverage, and more dramatic regime shifts than BTC?

## Scope
Pure quant signal analysis. NO SNN/neural-temporal models — those belong in the paired SNN task. This notebook tests: Linear → Ridge → Lasso → Random Forest → XGBoost → LightGBM → MLP.

## Design

### Assets (Shael's Picks)

**Controls:**
- BTC/USDT 4h (via ccxt — reference from V1, rerun with expanded horizons)
- ETH/USDT 4h (via ccxt — secondary reference)

**Solana DEX Tokens (via Birdeye API):**
- **JLP** (Jupiter Perps LP) — perp collateral-backed token with structural positive drift from funding rates. Crypto ETF dynamics. ~$3.6M daily vol.
- **KWEEN** — true microcap, thin orderbook, $5-10 trade sizes. *(Contract address TBD — Shael has helper doc)*
- **FARTCOIN** — Solana meme coin. May also have CEX listing.

**BNB Chain Tokens (via DexScreener/Bitquery or Binance CEX):**
- **$4** — meme coin on BNB chain *(exact contract TBD)*
- **BONK** — established meme coin *(confirm: Binance CEX or BNB chain DEX?)*
- **HYPER** — BNB chain *(exact token TBD)*
- **ASTER** (`0x000Ae...556A`) — DEX and perp hub on BNB. PancakeSwap V3. ~$381K daily vol.

**Asset registry with addresses, data sources, and quality gates:** `research/microcap_asset_registry.md`

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
- Shael's token list confirmed — see asset registry. Need contract addresses for: KWEEN, $4, HYPER
- Shael has a helper doc for KWEEN (thin orderbook handling) — incorporate when available
- JLP is structurally unique: funding rate accrual = positive drift. May need special baseline (predict deviation from drift, not raw return)
- BONK has deepest history if using Binance CEX listing (Solana original since late 2022)
- Transaction costs: 0.1% CEX (Binance), 0.3% DEX (Solana swap fees + slippage), 0.5% for thinnest tokens (KWEEN)
- This task produces QUANT-ONLY results. SNN experiments use these results as baseline reference.
