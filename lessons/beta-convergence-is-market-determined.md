---
primitive: lesson
date: 2026-03-15
source: V2 and V3 experiment results (93 models total)
confidence: high
project: snn-applied-finance
tags: [snn, hyperparameters, convergence]
applies_to: [snn-applied-finance]
downstream: []
---

# β Convergence Is Market-Determined

Across all architectures, encoding schemes, and model sizes, learnable β converges to 0.70–0.82 (τ = 3–5 candles = 12–20h at 4h resolution). This is NOT architecture-determined — it's the market's characteristic timescale for BTC at this resolution.

Implication: don't waste hyperparameter search on β when using learnable params. Initialize at 0.75 and let it find its level. The interesting question is whether different assets/timeframes converge to different β values.
