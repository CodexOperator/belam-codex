---
primitive: task
status: open
priority: high
created: 2026-03-25
owner: belam
depends_on: [quant-pairs-trading-energy-nuclear]
upstream: []
downstream: []
tags: [quant, microcap-swing, model-architecture]
---

## Teacher-Student: High-Confidence Label Distillation

### Goal
Use LGBM high-confidence predictions (>=0.80 threshold, 88-93% dir accuracy) as pseudo-labels to train student networks (ANN, SNN, LSTM) that can generalize the pattern to lower-confidence regions.

### Key Insight
At confidence >=0.80, LGBM achieves 88-93% directional accuracy but only fires on 5-15% of candles. A student network trained on these clean labels might learn the temporal structure of what precedes a high-confidence signal and fire earlier or on edge cases LGBM misses.

### Implementation Plan
1. Extract LGBM predictions where max class probability >= 0.80 from walk-forward CV
2. Use these as training labels (instead of raw triple-barrier labels)
3. Train student networks: LSTM (sequence model), ANN (feedforward), SNN (spiking)
4. Evaluate students on full dataset - do they maintain accuracy while increasing signal rate?
5. Compare student signal rate at matched accuracy to LGBM threshold gating

### SNN Training Variant
- Use the filtered high-confidence signals as spike timing targets
- SNN can naturally encode confidence as firing rate
- Rhythm neuron architecture maps well to regime persistence patterns
- Links directly to SNN applied finance research (w5)

### Success Criteria
- Student network achieves >85% dir accuracy on >20% of candles (vs LGBM's 88% on 15%)
- Signal quality maintained in walk-forward validation
- SNN variant demonstrates frequency-domain advantages
