---
primitive: decision
status: accepted
date: 2026-03-15
context: "Agents building SNN experiments need to make infrastructure choices — data storage, backtesting frameworks, GPU configuration, real-time pipelines. Wrong choices waste GPU hours and produce unreliable results."
alternatives:
  - "Let each agent figure out infrastructure independently (inconsistent choices)"
  - "Hardcode infrastructure in templates (inflexible)"
  - "Shared skill with best-practice recommendations (chosen)"
rationale: "Infrastructure decisions cascade — wrong data storage means slow backtests, wrong GPU config means wasted compute, wrong framework means unreproducible results. A shared skill ensures all agents make consistent, informed infrastructure choices."
consequences:
  - "Two-phase backtest workflow standardized: VectorBT PRO (discovery) → NautilusTrader (validation)"
  - "Data storage recommendations: QuestDB for time series, Polars over Pandas for transforms"
  - "GPU patterns: batch_size 4096, 2 CUDA streams, fp32 for T4 (from empirical SNN experiments)"
  - "Builder and critic share same infrastructure vocabulary"
project: quant-knowledge-skills
tags: [infrastructure, backtesting, gpu, data, knowledge]
knowledge: quant-infrastructure
cli: "R lessons (for infrastructure-related findings)"
downstream: [memory/2026-03-17_033419_built-two-major-systems-tonight-1-analys, memory/2026-03-17_134119_major-session-built-three-infrastructure]
promotion_status: exploratory
doctrine_richness: 10
contradicts: []
---

# Decision: Quant Infrastructure Skill

## Summary

Extracted production quant infrastructure knowledge into `knowledge/quant-infrastructure.md — `. Covers the full stack: data storage (QuestDB, kdb+, Polars), backtesting frameworks (VectorBT PRO, NautilusTrader), portfolio optimization (cvxpy, Riskfolio-Lib), compute hardware (GPU/TPU configuration), and real-time data pipelines.

## Key Recommendations

1. **Two-phase backtesting** — vectorized discovery (VectorBT PRO for 10K sweeps) then event-driven validation (NautilusTrader for order book replay)
2. **Polars over Pandas** — 5-10x faster for financial transforms, lazy evaluation prevents OOM
3. **QuestDB for time series** — columnar, time-partitioned, SQL interface, 1.5M inserts/sec
4. **T4 GPU config** — batch_size 4096, 2 CUDA streams, fp32 only (empirically validated on SNN experiments)
5. **Real-time pipeline** — Redpanda/Kafka → QuestDB → feature store → model inference

## Relevance to SNN Research

Builder agents use this skill when implementing Colab notebooks — it tells them optimal batch sizes, CUDA stream counts, and data loading patterns. Critic agents use it when reviewing code — checking that infrastructure choices follow best practices. The T4-specific optimizations came directly from our V3/V4 experiment runs.

## Related

- `decisions/two-phase-backtest-workflow.md` — the backtesting decision in detail
- `lessons/gpu-parallel-thrashing-t4.md` — T4-specific parallel execution lesson
- `lessons/tiny-snn-gpu-parallelism.md` — why small SNNs don't parallelize well on GPU
- `knowledge/quant-infrastructure.md` — full reference
