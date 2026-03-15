---
name: quant-infrastructure
description: Production quant finance infrastructure — data storage, backtesting frameworks, portfolio optimization, compute hardware, and real-time data pipelines. Use when designing or building data storage for financial time series, choosing backtesting frameworks, setting up portfolio optimization, configuring GPU/TPU compute for financial models, or architecting real-time market data ingestion. Also use when comparing frameworks (VectorBT vs NautilusTrader, QuestDB vs kdb+, Polars vs Pandas) or selecting data vendors.
---

# Quant Infrastructure

## Backtesting: Two-Phase Workflow

**Phase 1 — Vectorized Discovery (VectorBT PRO):**
- Strategies as N-dimensional NumPy arrays (Time × Asset × Param₁ × Param₂)
- Numba JIT compilation — 10K-parameter sweeps in minutes
- Built-in walk-forward and purged CV splitters
- WorldQuant 101 alphas as factor library
- Open-source version is maintenance-only; PRO is the standard

**Phase 2 — Event-Driven Validation (NautilusTrader):**
- Rust core + Python API
- Same strategy codepath in backtest and live (unified event stream)
- Models order book dynamics, execution latency, exchange-specific fill logic
- Critical for strategies where execution quality determines profitability

**AI-Driven Research (Microsoft Qlib):**
- 40+ SOTA models via YAML config (LightGBM, Transformer, LSTM)
- RD-Agent integration: LLM-powered factor discovery, ~2× returns, 70% fewer factors, <$10/run
- 15,000+ GitHub stars

**Avoid:** Backtrader (dead ~2018), Zipline-Reloaded (legacy, hard to install). Most institutional firms build custom systems.

## Data Storage

### Tick Data (choose by ecosystem)

| System | Strength | Benchmark |
|--------|----------|-----------|
| QuestDB | OHLCV queries, ASOF JOIN, nanosecond timestamps | 4.4× faster than kdb+ (25ms vs 109ms, 100M rows) |
| ArcticDB | Pandas/Polars integration, S3/LMDB, Bloomberg BQuant | Billions of rows, Man Group production |
| DuckDB | Research notebooks, embedded, zero-config | Parquet-native, no server needed |
| TimescaleDB | PostgreSQL ecosystem | Good if already on Postgres |

### Real-Time Ingestion Stack
- **Kafka:** Durable ordered event streaming
- **Redis Streams:** Low-latency pub/sub caches
- **ZeroMQ:** Ultra-low-latency brokerless fan-out (HFT)

### Data Vendors
- **Databento:** Historical US equities/futures, nanosecond resolution, pay-per-query
- **Polygon.io:** Real-time websockets — equities, options, crypto, forex (mid-tier)

## DataFrame Performance

**Polars > Pandas for >1M rows:**
- 2.6–11.7× faster (widest gap on sorting: 11.7×)
- Memory: 2–4× data size vs Pandas' 5–10×
- Lazy eval: predicate pushdown, column pruning, operation fusion
- 2025 streaming engine: additional 3–7× over in-memory
- Use Pandas only for <1M rows, legacy codebases, quick exploration

## Portfolio Optimization

**Foundation:** `cvxpy` + MOSEK solver

**Modern library:** `skfolio` (2024)
- Scikit-learn compatible interface
- MeanRisk, HRP, Black-Litterman, entropy pooling, distributionally robust optimization
- Built-in CombinatorialPurgedCV

**Transaction cost models:**
- Linear: TC = a·|trade_value| (1–5 bps liquid US equities)
- Quadratic: + b·trade² for market impact
- 3/2-power (Cvxportfolio): a·|trade| + b·|trade|^{3/2} — best empirical fit

**HRP advantage:** No matrix inversion, works on singular covariance, consistently lower OOS variance than mean-variance.

## Compute Hardware

For detailed GPU/TPU optimization patterns, see [references/compute.md](references/compute.md).

Key rules:
- Hyperparameter sweeps on T4 (cheap), final training on H100/A100
- BF16 on Ampere+ (no loss scaling, wider dynamic range than FP16)
- TF32 auto-enabled on Ampere+: free 3× matmul speedup
- torch.compile(): 1.5–3× on repetitive loops
- Batch size scaling: when doubling batch, multiply LR by √2
