---
title: SNN Deep Analysis — Foundational V1/V2
status: done
priority: high
tags: snn, research, analysis, deep-dive
pipeline: snn-deep-analysis-foundational-v1-v2
project: snn-applied-finance
created: 2026-03-31
---

# SNN Deep Analysis — Foundational V1/V2

Deep research analysis of the foundational SNN crypto predictor notebooks (V1 stock, V1 crypto, V2).

## Scope

Analyze the following notebooks:
1. `machinelearning/llm-quant-finance/notebooks/snn_stock_predictor.ipynb`
2. `machinelearning/llm-quant-finance/notebooks/snn_crypto_predictor.ipynb`
3. `machinelearning/llm-quant-finance/notebooks/snn_crypto_predictor_v2.ipynb`

## Deliverables

1. **Cost function analysis** — What parameters vs hyperparameters the loss adjusts (weights, biases, β, thresholds, learning rate)
2. **Encoding/decoding deep dive** — ANN/LSTM embedding (continuous activations) vs SNN embedding (spike trains via population coding). Include:
   - Direct math derivations with LaTeX
   - Python scripts that generate rich visualizations of encoding/decoding transformations
   - Worked numerical examples
3. **Neuron communication during training** — How presynaptic spikes propagate, the LIF equation, surrogate gradient, membrane dynamics
4. **Network topology diagrams** — Layer-by-layer architecture maps, neuron counts, connection patterns, information flow over timesteps
5. **Generated visualizations** — All diagrams produced by Python scripts (matplotlib/seaborn), saved as PNGs

## Reference Material

Pre-analysis written by Opus available at:
`machinelearning/snn_applied_finance/research/deep_analysis/01_foundational_v1_v2.md`

Builder should use this as a starting reference but must read the actual notebooks, write Python visualization scripts, execute them, and compile results into a rich illustrated report.

## Output Location

All scripts and outputs go to: `machinelearning/snn_applied_finance/research/deep_analysis/foundational_v1_v2/`
