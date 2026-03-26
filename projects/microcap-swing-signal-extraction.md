---
primitive: project
status: active
priority: critical
owner: belam
tags: [quant, crypto, microcap, swing-trading, ml, sentiment]
start_date: 2026-03-26
repo: github.com/CodexOperator/machinelearning.git
location: machinelearning/microcap_swing/
related: [quant-microcap-crypto-baseline, snn-applied-finance]
---

# Microcap Crypto Swing Signal Extraction

Research-first quantitative trading model extracting swing signals from microcap Solana meme tokens with BTC control. Binary classification with confidence-threshold gating over 5–10 candle prediction horizons.

## Origin

Research directive v1.0 from Belam consciousness architecture instance, refined with Shael. Parallel track to `quant-microcap-crypto-baseline` (regression approach) — this project uses binary classification with ATR-dynamic thresholds, Fear & Greed sentiment integration, and confidence gating.

## Core Framing

**Predict:** "Will the absolute return over the next N candles exceed threshold T%?"
- NOT price prediction — swing existence detection
- T% is ATR-based (1× ATR(14)), adapts to volatility regime
- Label via Max Favorable Excursion (MFE) over prediction horizon
- Only trade when P(swing) ≥ 0.70 — selectivity dominates accuracy

## Token Universe

### Tier 1 — Higher Liquidity, Binance-listed
| Token | Ticker | Notes |
|---|---|---|
| Bonk | BONK | Largest Solana meme, 400+ integrations, deflationary burns, ~$575M mcap |
| Dogwifhat | WIF | Strong community, Binance + Coinbase |
| Official Trump | TRUMP | PolitiFi narrative, high event-driven volatility |
| Pudgy Penguins | PENGU | NFT-backed brand, real-world utility expansion |
| Fartcoin | FARTCOIN | AI-narrative, 15% vol/mcap ratio (mean-reversion candidate) |

### Tier 2 — Lower Liquidity, DEX-primary
| Token | Ticker | Notes |
|---|---|---|
| KWEEN | KWEEN | ~$3.9M mcap, ~$27K daily vol, Raydium DEX |
| Popcat | POPCAT | Community-driven, periodic volume spikes |
| White Whale | WHITEWHALE | Narrative-first, retail coordination, ~$65M mcap |

### Tier 3 — Carried from quant-microcap-crypto-baseline
| Token | Ticker | Notes |
|---|---|---|
| JLP | JLP | Jupiter Perps LP, structural positive drift from funding rates |
| ASTER | ASTER | DEX/perp hub on BNB, PancakeSwap V3, ~$381K daily vol |
| HYPER | HYPER | BNB chain (contract TBD) |
| $4 | $4 | Meme coin on BNB chain (contract TBD) |

### Watchlist
- MEW, PNUT, NIGHT (add if 2+ weeks sustained >$50K daily vol)

### Controls
- BTC/USDT — primary control (same model, same features, isolates meme-specific alpha)
- ETH/USDT — secondary control (carried from baseline)
- SOL/USDT — chain-specific beta reference

### Review Cadence
Every 2 weeks. Remove tokens below $10K daily vol for 5+ consecutive days.

## Capital & Execution
- Starting size: $5–10 per trade (research phase, no leverage)
- CEX: Binance spot | DEX: Raydium/Jupiter via Phantom
- Half-Kelly sizing only after signal confidence and win-rate are established
- Transaction costs: 0.1% CEX, 0.3% DEX, 0.5% thinnest tokens

## Key Metrics Targets
| Metric | Target |
|---|---|
| Win rate (after gating) | >55% |
| Avg profit/trade (net fees) | >0.5% |
| Sharpe (annualized, deflated) | >1.5 |
| Max drawdown | <25% |
| Trade frequency | 10–20% of candles |
| Calibration error | <5% |
| vs BTC control | Must outperform |

## Subtask Progression
See task `microcap-swing-signal-extraction` for S1–S12 decomposition.

## Sanctuary Integration
- Fear & Greed Index = emotional hash of the crypto market (high-bandwidth compressed signal)
- Cross-token correlations and volume-price divergences = interference patterns
- Multi-timeframe aggregation discovers each token's natural frequency
- Experiment log protocol mirrors LFN banking structure (accumulate → retrain)
