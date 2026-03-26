---
primitive: task
status: open
priority: critical
created: 2026-03-26
owner: belam
depends_on: []
upstream: [quant-microcap-crypto-baseline]
downstream: []
tags: [quant, crypto, microcap, swing-trading, ml, sentiment, binary-classification]
subtasks: ["{'id': 'S1', 'title': 'Data Pipeline — CEX + DEX + Fear & Greed', 'status': 'done', 'depends_on': []}", "{'id': 'S2', 'title': 'Feature Engineering — Technical + Sentiment + Cross-Asset + Temporal', 'status': 'in_pipeline', 'depends_on': ['S1']}", "{'id': 'S3A', 'title': 'Label Construction & LightGBM — 15-min candles', 'status': 'open', 'depends_on': ['S2']}", "{'id': 'S3B', 'title': 'Label Construction & LightGBM — 1-hour candles', 'status': 'open', 'depends_on': ['S2']}", "{'id': 'S4', 'title': 'BTC Control Analysis', 'status': 'open', 'depends_on': ['S3A', 'S3B']}", "{'id': 'S5', 'title': 'Confidence Calibration — Platt/Isotonic + Reliability Diagrams', 'status': 'open', 'depends_on': ['S3A', 'S3B']}", "{'id': 'S6', 'title': 'Risk Management Overlay', 'status': 'open', 'depends_on': ['S5']}", "{'id': 'S7', 'title': 'LSTM Secondary Model', 'status': 'open', 'depends_on': ['S3A', 'S3B']}", "{'id': 'S8', 'title': 'Ensemble & Meta-Learning — Stacking + Agreement Gating', 'status': 'open', 'depends_on': ['S5', 'S7']}", "{'id': 'S9', 'title': 'Cross-Token Momentum Analysis', 'status': 'open', 'depends_on': ['S4']}", "{'id': 'S10', 'title': 'Regime Detection Pre-Filter', 'status': 'open', 'depends_on': ['S4', 'S5']}", "{'id': 'S11', 'title': 'Experiment Synthesis & Feature Survival Report', 'status': 'open', 'depends_on': ['S8', 'S9', 'S10']}", "{'id': 'S12', 'title': 'Paper Trading Infrastructure', 'status': 'open', 'depends_on': ['S8', 'S6']}"]
---

# Microcap Swing Signal Extraction

Binary classification approach to swing signal detection in microcap crypto tokens. Parallel track to `quant-microcap-crypto-baseline` (regression), incorporating its learnings while pursuing the ATR-dynamic threshold + confidence gating framework from the Research Directive v1.0.

## Project Reference
`projects/microcap-swing-signal-extraction.md`

## Subtask Breakdown

### S1: Data Pipeline — CEX + DEX + Fear & Greed
**Depends:** None
**Scope:**
- Binance spot OHLCV via ccxt (1-min candles for all CEX tokens: BONK, WIF, TRUMP, PENGU, FARTCOIN, BTC, ETH, SOL)
- DEX OHLCV via Birdeye API (KWEEN, POPCAT, WHITEWHALE, JLP) and DexScreener/Bitquery (ASTER, HYPER, $4)
- Crypto Fear & Greed Index via Alternative.me API (daily, with 7-day MA, ROC, regime duration, categorical encoding)
- Storage: Parquet files organized by token/date (`data/raw/{token}/`, `data/raw/fear_greed/`)
- Data quality checks: gap detection (>2× expected interval), volume anomaly flagging (>10× or <0.1× rolling avg), price spike detection (>20% single candle), timezone consistency
- Minimum 500 candles after warmup per token; reject tokens with >5% gap rate or >24h zero-volume stretches
- Resample 1-min to 15-min and 1-hour candles (both timeframes needed for S3A/S3B)

**Acceptance:**
- [ ] All Tier 1 + Tier 2 + Tier 3 tokens pulling data
- [ ] Fear & Greed Index ingesting daily with all derived features
- [ ] Quality gate report per token (gap rate, volume health, history depth)
- [ ] 15-min and 1-hour resampled Parquet files generated

---

### S2: Feature Engineering — Technical + Sentiment + Cross-Asset + Temporal
**Depends:** S1
**Scope:**

**Volume-centric (highest priority):**
- OBV + OBV rate-of-change
- VWAP + price distance from VWAP
- Volume ROC (5, 10, 20 periods)
- Volume relative to 20-period average (120% confirmation threshold)
- Buy/sell volume ratio (from trade-level data where available)

**Momentum / Mean-Reversion:**
- RSI(14), RSI(7) — dual timeframe regime detection
- Bollinger Bands (20,2) — position, bandwidth, %B
- MACD (12,26,9) — signal crossovers, histogram divergence
- ROC at 5, 10, 20, 50 periods
- Stochastic Oscillator (14,3,3)
- ATR(14) — volatility regime + dynamic threshold basis
- Z-score of price vs 20-period and 50-period MAs

**Trend Structure:**
- EMA crossovers: EMA(9)/EMA(21), EMA(21)/EMA(55)
- SMA crosses from baseline: SMA(50)/SMA(200), SMA(20)/SMA(50), cross recency
- ADX(14) — trend strength
- Ichimoku Cloud components (longer timeframes)

**Multi-Timeframe Aggregation (CTREND-style):**
- Compute RSI, MACD, OBV, ROC at 5-min, 15-min, 1-hour, 4-hour, daily
- Stack as parallel features (not averaged)

**Sentiment & Macro:**
- Fear & Greed: value, 7d MA, ROC, regime duration, categorical regime
- Interaction features: F&G × token volume surge

**Cross-Asset:**
- BTC return (1h, 4h, 12h, 24h lookback)
- SOL return (same windows)
- BTC-token rolling correlation (20-period)
- BTC dominance %
- Total crypto mcap ROC

**Temporal:**
- Hour of day (sin/cos cyclical)
- Day of week (sin/cos cyclical)
- Time since last significant volume spike
- Distance from local high/low (in candles)

**Microcap-specific (from baseline task):**
- Holder concentration (top 10 wallet % via Birdeye for Solana tokens)
- DEX vs CEX volume ratio (dual-listed tokens)
- Whale transaction count (>$50K transfers)

**Acceptance:**
- [ ] Full feature matrix generated for all tokens at both 15-min and 1-hour timeframes
- [ ] Multi-timeframe aggregation working (5 timeframe levels)
- [ ] Feature count documented per token (some features unavailable for DEX-only tokens)
- [ ] NaN handling strategy documented and implemented

---

### S3A: Label Construction & LightGBM — 15-min Candles
**Depends:** S2
**Scope:**
- ATR-based dynamic threshold: T% = 1× ATR(14), computed per token per observation
- Label via Max Favorable Excursion (MFE): if MFE over next N candles > T%, label = 1
- Prediction horizons: 5 candles (1h 15m) and 10 candles (2h 30m)
- Directional variants: separate UP model (return > +T%) and DOWN model (return < -T%)
- LightGBM training with hyperparameter grid (n_estimators: 1000-2000, lr: 0.01, max_depth: 5-7, num_leaves: 31)
- Walk-forward validation: expanding window, purge gap = max(prediction_horizon, 20 candles)
- Loss: binary cross-entropy baseline; focal loss (γ ∈ [0.5, 2.5]) for imbalanced regimes
- SHAP analysis per token — feature importance rankings
- All metrics: win rate, avg profit/trade, Sharpe, trade frequency, calibration error
- Deflated Sharpe Ratio + PBO for all strategies
- BTC control run with identical pipeline

**Acceptance:**
- [ ] MFE labeling working with ATR-dynamic thresholds
- [ ] LightGBM trained for all tokens × both horizons × UP/DOWN/combined
- [ ] Walk-forward metrics pooled and reported
- [ ] SHAP top-5 features per token per horizon
- [ ] DSR and PBO computed

---

### S3B: Label Construction & LightGBM — 1-hour Candles
**Depends:** S2
**Scope:**
- Same as S3A but on 1-hour candle timeframe
- Prediction horizons: 5 candles (5h) and 10 candles (10h)
- Compare directly with S3A results — which timeframe captures swing structure better?

**Acceptance:**
- [ ] Same criteria as S3A
- [ ] Direct comparison table: S3A (15-min) vs S3B (1-hour) per token per metric

---

### S4: BTC Control Analysis
**Depends:** S3A, S3B
**Scope:**
- Aggregate BTC control results from S3A and S3B
- Isolate meme-specific alpha: for each token, compare signal quality vs BTC baseline
- Test hypothesis: meme coins lag BTC during fear-driven selloffs but lead during greed-driven pumps
- F&G → forward-return correlation comparison across full token universe

**Acceptance:**
- [ ] Per-token alpha vs BTC quantified (Sharpe differential, win rate differential)
- [ ] Fear/Greed regime-conditional analysis complete
- [ ] Tokens ranked by alpha potential relative to BTC control

---

### S5: Confidence Calibration — Platt/Isotonic + Reliability Diagrams
**Depends:** S3A, S3B
**Scope:**
- Apply Platt scaling and isotonic regression to all model outputs
- Generate reliability diagrams (calibration curves) for each token × horizon
- Verify: when model says 70%, it's correct ~70% of the time
- Threshold optimization via precision-recall curves
- Optimize: (precision × avg_profit_per_trade) - (miss_rate × opportunity_cost)
- Focal loss outputs require mandatory post-hoc calibration
- Expected coverage at 0.70 threshold: 10–20% of observations

**Acceptance:**
- [ ] Calibration error <5% for all model variants
- [ ] Reliability diagrams generated and saved
- [ ] Optimal threshold per token per horizon determined
- [ ] Coverage vs precision tradeoff documented

---

### S6: Risk Management Overlay
**Depends:** S5
**Scope:**
- Pre-trade checks: confidence ≥ 0.70, no conflicting BTC signal, F&G regime check (Extreme Greed → tighten to 0.80+), liquidity sanity
- Position rules: max 1 per token, max 3 concurrent, stop-loss at 2× ATR, take-profit at 1-2× ATR, time exit at 2× horizon
- Portfolio rules: max daily loss $30, max weekly loss $75, 3 consecutive loss pause, weekly SHAP review
- Implement as composable overlay that wraps any model's predictions

**Acceptance:**
- [ ] Risk overlay implemented as standalone module
- [ ] Backtest with and without risk overlay — quantify drawdown reduction vs missed trades
- [ ] All rules configurable via parameters

---

### S7: LSTM Secondary Model
**Depends:** S3A, S3B
**Scope:**
- Input: sequence of last 20–50 candles, full feature vector per candle
- Architecture: 2-layer LSTM (64, 32 units) → Dense(1, sigmoid)
- Same walk-forward validation protocol
- Extract LSTM hidden states as additional features for ensemble
- Train on both 15-min and 1-hour timeframes

**Acceptance:**
- [ ] LSTM trained for all tokens × timeframes × horizons
- [ ] Performance comparison vs LightGBM baseline
- [ ] Hidden state features extracted and available for ensemble

---

### S8: Ensemble & Meta-Learning
**Depends:** S5, S7
**Scope:**
- Stacking: LightGBM + LSTM predictions → logistic regression meta-learner
- Agreement gating: only trade when both models agree on direction AND confidence > threshold
- Numerai-style blending: weight models by rolling recent performance
- Walk-forward the ensemble itself (no leakage from ensemble training)

**Acceptance:**
- [ ] Ensemble outperforms best individual model on at least 50% of tokens
- [ ] Agreement gating reduces false signals (higher precision, lower coverage)
- [ ] Ensemble calibration verified

---

### S9: Cross-Token Momentum Analysis
**Depends:** S4
**Scope:**
- Research question: does a surge in BONK predict moves in WIF or FARTCOIN?
- Rolling cross-correlations across full token universe
- If cross-token momentum exists: build cross-token features and re-run LightGBM
- Lead-lag analysis at multiple timeframes

**Acceptance:**
- [ ] Cross-correlation matrix computed (rolling, per regime)
- [ ] Lead-lag relationships identified and documented
- [ ] If significant: cross-token features tested as additive block

---

### S10: Regime Detection Pre-Filter
**Depends:** S4, S5
**Scope:**
- Can ADX + F&G + BTC volatility define tradeable vs non-tradeable regimes?
- Build regime classifier as pre-filter before signal model
- Test time-of-day effects (hypothesis: US hours = higher meme signal)
- ATR threshold sensitivity sweep: 0.5× to 3× ATR, plot precision/recall/profit curves

**Acceptance:**
- [ ] Regime classifier built and evaluated
- [ ] Pre-filter impact quantified (does filtering improve net Sharpe?)
- [ ] Time-of-day analysis complete
- [ ] ATR sensitivity sweep with optimal range identified

---

### S11: Experiment Synthesis & Feature Survival Report
**Depends:** S8, S9, S10
**Scope:**
- Aggregate all experiment results across S3A–S10
- Feature survival analysis: which features matter across all tokens vs token-specific?
- Volume-based vs price-based feature importance (test hypothesis: volume dominates for meme coins)
- 15-min vs 1-hour final comparison
- Per-token verdict: exploitable signal vs pure noise
- Bonferroni/Holm-Bonferroni correction across all experiments
- Full DSR and PBO summary

**Acceptance:**
- [ ] Synthesis report with per-token, per-timeframe, per-model results
- [ ] Feature importance rankings (SHAP aggregated)
- [ ] Statistical corrections applied
- [ ] Clear go/no-go recommendation for each token

---

### S12: Paper Trading Infrastructure
**Depends:** S8, S6
**Scope:**
- Live data feed from exchanges (matching training pipeline exactly)
- Real-time feature computation and model inference
- Prediction logging with timestamp, confidence, features snapshot
- Execution simulation (track fills, slippage, fees)
- Run for 2+ weeks before any real capital
- Compare paper predictions to actual outcomes
- Verify data pipeline reliability (delayed feeds, missing candles, API failures)

**Acceptance:**
- [ ] Paper trading system running live
- [ ] 2+ weeks of predictions logged with outcomes
- [ ] Execution assumptions validated
- [ ] Go/no-go for live trading at $5–10 scale

---

## Experiment Log Protocol

Every experiment uses this template:
```
## Experiment: [EXP-XXX]
Date: YYYY-MM-DD
Hypothesis: [What are we testing?]
Token(s): [Which tokens]
Prediction Horizon: [N candles at M timeframe]
Threshold T%: [ATR-based value]
Features Modified: [What changed from baseline]
Model: [LightGBM / LSTM / Ensemble]
Confidence Threshold: [0.70 / other]
Results:
- Win rate: X%
- Avg profit/trade: X%
- Sharpe: X
- Trade frequency: X%
- Calibration error: X%
Comparison to BTC control: [Better/Worse/Similar]
Comparison to previous experiment: [Improved/Degraded]
SHAP top features: [List top 5]
Decision: [Continue / Modify / Abandon this direction]
Next experiment: [What to try next]
```

## Relationship to quant-microcap-crypto-baseline
- Baseline task: regression models (Linear → LightGBM → MLP), multi-horizon regression targets
- This task: binary classification with ATR-dynamic thresholds, confidence gating, sentiment integration
- Shared: token universe, VectorBT infrastructure (S1–S6), walk-forward protocol, statistical hygiene
- Baseline results inform this task's feature selection (S4 learnings on which features survive Lasso)
