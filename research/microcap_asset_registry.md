# Microcap Asset Registry — Quant Baseline V2

## Control Assets
| # | Ticker | Name | Chain | Source | 24h Vol | Notes |
|---|--------|------|-------|--------|---------|-------|
| 0 | BTC/USDT | Bitcoin | CEX | ccxt (Binance) 4h | Massive | V1 reference, rerun with expanded horizons |
| 0 | ETH/USDT | Ethereum | CEX | ccxt (Binance) 4h | Massive | Secondary reference |

## Microcap Token List (Shael's Picks)

### Solana Tokens
| # | Ticker | Name | Contract Address | Primary DEX | Data Source | 24h Vol | Liquidity | Notes |
|---|--------|------|-----------------|-------------|-------------|---------|-----------|-------|
| 1 | **JLP** | Jupiter Perps LP | `27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4` | Orca | Birdeye/DexScreener | ~$3.6M | ~$24M+ | Backed by Jup perp collateral. Structural positive drift from funding rates. Crypto ETF dynamics. **Unique: predict deviation from drift, not raw return.** |
| 2 | **KWEEN** | DO KWEEN | `DEf93bSt8dx58gDFCcz4CwbjYZzjwaRBYAciJYLfdCA9` | Raydium | Birdeye/DexScreener | ~$5.5K | ~$79K | True microcap. Thin orderbook. $5-10 trade sizes. Shael has helper doc for orderbook handling. |
| 3 | **FARTCOIN** | Fartcoin | `9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump` | Raydium/Pumpswap | Birdeye/DexScreener | Varies | Varies | Meme coin. May also have CEX listing. |
| 4 | **BONK** | Bonk | `DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263` | Meteora/Raydium | Birdeye/ccxt (Binance) | ~$905K (DEX) | Substantial | Original Solana BONK. Also listed on Binance CEX (BONK/USDT) — deepest history via ccxt. Since late 2022. |

### BNB Chain Tokens
| # | Ticker | Name | Contract Address | Primary DEX | Data Source | 24h Vol | Notes |
|---|--------|------|-----------------|-------------|-------------|---------|-------|
| 5 | **$4** | 4 | `0x0A43fC31a73013089DF59194872Ecae4cAe14444` | PancakeSwap V2 | DexScreener/Bitquery | ~$784K | Meme coin on BSC. Active trading (~5.8K txns/24h). ~$0.012. |
| 6 | **ASTER** | Aster | `0x000Ae314E2A2172a039B26378814C252734f556A` | PancakeSwap V3 + Aster DEX | DexScreener/Bitquery + Aster API | ~$382K | DEX and perp hub on BNB. ~$0.66. **Dual source:** PancakeSwap for spot OHLCV, Aster's own API for perp data/orderbook depth/funding rates. |

### HyperEVM Token
| # | Ticker | Name | Native Chain | Data Source | 24h Vol | Notes |
|---|--------|------|-------------|-------------|---------|-------|
| 7 | **HYPE** | Hyperliquid | HyperEVM (L1) | Hyperliquid API / DexScreener (HyperEVM) | ~$302K (DEX) + CEX | Native L1 token. Data via Hyperliquid's own candle API. Also tradeable on HyperEVM DEXs. |

## Perp Data Coverage — Dual Source

### Hyperliquid (229 markets) — `POST https://api.hyperliquid.xyz/info`
### Aster DEX (329 markets) — `https://fapi.asterdex.com/fapi/v1/`

| Token | Hyperliquid | Aster DEX | Exotic Data |
|-------|------------|-----------|-------------|
| BTC | ✅ `BTC` | ✅ `BTCUSDT` | Funding, OI, orderbook, liquidations |
| ETH | ✅ `ETH` | ✅ `ETHUSDT` | Same |
| BONK | ✅ `kBONK` | ✅ `1000BONKUSDT` | Same |
| FARTCOIN | ✅ `FARTCOIN` | ✅ `FARTCOINUSDT` | Same |
| HYPE | ✅ `HYPE` | ✅ `HYPEUSDT` | Same |
| ASTER | ✅ `ASTER` | ✅ `ASTERUSDT` | Same |
| $4 | ❌ | ✅ `4USDT` | **Aster only** — funding, OI, orderbook |
| SOL | ✅ `SOL` | ✅ `SOLUSDT` | Same |
| JLP | ❌ | ❌ | N/A (spot only) |
| KWEEN | ❌ | ❌ | N/A (too small for perps) |

**8 of 9 assets have perp data** from at least one source. Only JLP and KWEEN lack perp coverage.
$4 is Aster-only. All others have dual-source perp data (cross-exchange comparison possible).

Exotic features available from both APIs:
- Funding rates (direct leverage sentiment)
- Open interest + OI delta (crowding detection)
- L2 orderbook depth (bid/ask imbalance)
- Liquidation data (cascade prediction)
- Kline/candlestick history
- Aggregate trades

### Aster API Reference
- Docs: `https://asterdex.github.io/aster-api-website/futures/general-info/`
- Base: `https://fapi.asterdex.com`
- Binance-compatible REST API (same endpoint patterns: `/fapi/v1/klines`, `/fapi/v1/depth`, `/fapi/v1/fundingRate`)
- No API key needed for market data endpoints
- Rate limit: 2400 request weight/min

Note: HYPER and HYPE are separate tokens on both exchanges.

## Data Pipeline Design

### Tier 1: ccxt (CEX — deepest history)
- BTC/USDT, ETH/USDT, BONK/USDT — Binance 4h candles
- Paginate for full history (years of data)
- Most reliable, cleanest OHLCV

### Tier 2: Birdeye API (Solana DEX)
- JLP, KWEEN, FARTCOIN — Solana tokens without reliable CEX listings
- `GET /defi/ohlcv?address={addr}&type=4H`
- Max 1000 records/call → paginate
- Requires API key (free tier available)
- Cache to CSV

### Tier 3: DexScreener + Bitquery (BNB Chain)
- $4, ASTER — BSC tokens
- DexScreener for discovery/metadata/validation
- Bitquery V2 GraphQL for historical OHLCV reconstruction from trades
- Alternative: if listed on any CEX, use ccxt instead

### Tier 4: Aster DEX API (ASTER — dual source)
- Aster's own DEX/perp API for: orderbook depth, funding rates, perp OHLCV, open interest
- PancakeSwap (via Bitquery/DexScreener) for spot OHLCV
- Dual-source comparison: spot vs perp dynamics as features
- Aster perp data is exotic feature material — funding rates, OI, liquidations directly from the protocol

### Tier 5: Hyperliquid API (HYPE)
- Hyperliquid REST API: `POST /info` with `{"type": "candleSnapshot", "coin": "HYPE", "interval": "4h", "startTime": ...}`
- Returns OHLCV candles natively — clean, no reconstruction needed
- Also available on HyperEVM DEXs via DexScreener

## Data Quality Gates
| Tier | Min Candles (4h) | Max Gap Rate | Max Zero-Vol Stretch |
|------|-----------------|-------------|---------------------|
| CEX (BTC, ETH, BONK) | 2000+ | <1% | <4h |
| DEX Established (JLP, FARTCOIN, $4, ASTER) | 500+ (~83 days) | <5% | <24h |
| DEX Microcap (KWEEN) | 300+ (~50 days) | <10% | <48h (documented) |

## Transaction Cost Model
| Source | Cost per Trade | Notes |
|--------|---------------|-------|
| Binance CEX | 0.10% | Taker fee |
| Solana DEX (Jupiter/Raydium) | 0.30% | Swap fee + slippage estimate |
| BSC DEX (PancakeSwap) | 0.25% | Swap fee |
| Thin orderbook (KWEEN) | 0.50% | Higher slippage at $5-10 size |

## Special Modeling Notes

### JLP: Drift-Adjusted Target
JLP accrues value from funding rates → structural positive drift. Models should predict:
- **Primary:** deviation from expected drift (detrended return)
- **Secondary:** raw return (for comparison with V1 methodology)
- Drift estimate: rolling 30-day average return as baseline

### KWEEN: Thin Orderbook Handling
- Shael has helper doc (to be incorporated)
- Volume-weighted features may be unreliable at low volume
- Consider: bid-ask proxy from high-low range as feature
- May need to use 1d candles instead of 4h if 4h data is too sparse

### BONK: Dual Data Source
- Use Binance CEX (ccxt) as primary — deeper history, cleaner data
- Use Solana DEX (Birdeye) as secondary — can compare CEX vs DEX pricing dynamics
- Cross-source spread itself could be a feature

## Action Items
- [x] KWEEN contract address confirmed
- [x] $4 contract address confirmed
- [x] BONK confirmed as original Solana BONK
- [x] HYPE confirmed as Hyperliquid native L1 token (HyperEVM)
- [ ] Test Birdeye API key access
- [ ] Test Bitquery V2 for BSC token history
- [ ] Get KWEEN helper doc from Shael
