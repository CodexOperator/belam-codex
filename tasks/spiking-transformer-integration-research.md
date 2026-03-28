---
primitive: task
status: open
priority: medium
created: 2026-03-21
owner: belam
project: snn-applied-finance
depends_on: []
upstream: []
downstream: [quant, microcap-swing, model-architecture]
tags: [snn, transformer, temporal, research]
---

## ANN Topology Exploration: TabNet, Temporal CNN, Transformer

### Goal
Evaluate alternative neural network architectures on the microcap swing dataset as potential replacements or complements to LSTM.

### Architectures to Test

**TabNet** (attention-based tabular)
- Designed for structured/tabular data like our feature matrix
- Built-in feature selection via attention masks
- Should handle the 40-60 feature space well
- Interpretable: shows which features it attends to per prediction

**Temporal CNN** (1D convolutions)
- Faster than LSTM, captures local sequential patterns
- Dilated convolutions can span long ranges efficiently
- WaveNet-style architecture for multi-scale temporal patterns
- Could replace LSTM as the sequential signal generator for t8

**Transformer with positional encoding**  
- Self-attention learns which past candles matter most
- Can attend to distant history without vanishing gradients
- Positional encoding captures temporal structure
- Heavy on compute for long sequences - use windowed attention

### Evaluation Framework
- Same walk-forward CV as LGBM (5-fold, 48-candle purge)
- Compare: accuracy, lift, bull recall, bear F1
- Feature: which architecture best complements LGBM in stacking?
- Compute cost vs accuracy tradeoff

### Priority Order
1. TabNet (most likely to work, least compute, most interpretable)
2. Temporal CNN (fast, good for signal generation pipeline)
3. Transformer (highest potential ceiling, most compute)

### Dependencies
- None strict, but benefits from t5 (higher-TF features) for richer input
