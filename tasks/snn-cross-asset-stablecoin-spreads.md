---
primitive: task
status: open
priority: high
created: 2026-03-25
owner: belam
depends_on: [quant-cross-asset-stablecoin-spreads]
upstream: [quant-baseline-v1]
downstream: []
tags: [quant, microcap-swing, model-architecture]
---

## Specialist Stacking: LSTM + LGBM Cross-Model Ensemble

### Goal
Combine LSTM and LightGBM probability outputs into a proper stacking ensemble that exploits their complementary strengths.

### Key Insight
LSTM has high bull recall (62%) but low precision (31%). LGBM has high bull precision (62%) but low recall (28%). Stacking should AND these signals for high-precision, moderate-recall bull detection.

### Implementation Plan
1. Enable `use_lstm=True` in synthesis config for 30m timeframe
2. Run LSTM at both 15m and 30m to get probability outputs
3. Feed [LGBM_P(bear,chop,bull), LSTM_P(bear,chop,bull)] as 6-dim feature vector to meta-learner
4. Train meta-learner (logistic, small LGBM, small NN) with strict walk-forward splits
5. Evaluate on same CV scheme as base models
6. Compare: ensemble dir_acc vs best single model, especially bull recall + precision

### Cross-Timeframe Variant
- Stack 15m LGBM + 30m LGBM + 15m LSTM + 30m LSTM = 12-dim stacking vector
- This captures both temporal scale diversity AND model type diversity

### Success Criteria
- Ensemble lift > best single model by >0.5%
- Bull F1 improvement over LGBM alone
- No degradation in bear detection

### Dependencies
- Current multi-TF run must complete (BTC, ETH, SOL done)
- LSTM needs to run at 30m (currently only 15m)
