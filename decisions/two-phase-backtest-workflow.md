---
primitive: decision
status: accepted
date: 2026-03-15
context: Production Quant Handbook — backtesting architecture for all trading strategy research
alternatives: [single framework, custom build, vectorized only, event-driven only]
rationale: Industry standard 2025-2026. Vectorized (VectorBT PRO) for high-throughput discovery and parameter sweeps. Event-driven (NautilusTrader) for production-fidelity validation with order book replay and exchange-accurate fills. Two phases cover speed and realism.
consequences: [Use VectorBT PRO for parameter sweeps and robustness analysis, Use NautilusTrader for final validation before paper trading, Microsoft Qlib for AI-driven factor discovery]
project: snn-applied-finance
tags: [backtesting, infrastructure, workflow]
downstream: [memory/2026-03-17_134119_major-session-built-three-infrastructure]
---

# Two-Phase Backtest Workflow

Discovery: VectorBT PRO (10K sweeps in minutes) → Validation: NautilusTrader (order book replay, latency modeling).
