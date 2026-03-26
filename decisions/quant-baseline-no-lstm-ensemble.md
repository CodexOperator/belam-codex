---
primitive: decision
status: proposed
date: 2026-03-26
context: "LSTM (S7) and ensemble meta-learners (S8) added zero lift over quant floor models in microcap swing pipeline"
alternatives: ["Keep LSTM/ensemble in future iterations", "Drop LSTM/ensemble from quant baseline"]
rationale: "S8 ensemble report: all strategies converged at 63.5% accuracy, F1(bull)=0, zero lift over best individual LightGBM. LSTM showed no advantage over LightGBM on microcap swing data. Adds compute cost and complexity without signal."
consequences: ["Future quant baseline iterations use only: Linear, Ridge, Lasso, RF, XGBoost, LightGBM, MLP", "No temporal neural models or ensemble meta-learners in quant baseline pipeline", "SNN research continues as separate track"]
upstream: [microcap-swing-signal-extraction]
downstream: []
tags: [quant, crypto, microcap]
status: accepted
---

# quant-baseline-no-lstm-ensemble

## Context

S7 (LSTM) and S8 (Ensemble & Meta-Learning) completed in the microcap swing pipeline. Results show zero signal improvement over standard quant models.

## Decision

Future quant baseline iterations exclude LSTM and ensemble meta-learners. Stick to: Linear, Ridge, Lasso, RF, XGBoost, LightGBM, MLP. SNN research continues on its own track.

## Consequences

Simpler pipeline, faster iteration, no loss of signal quality.
