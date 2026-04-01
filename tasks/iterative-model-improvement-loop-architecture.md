---
primitive: task
status: open
priority: high
created: 2026-03-28
owner: belam
depends_on: [specialist-stacking-lstm-lgbm-cross-model-ensemble, teacher-student-high-confidence-distillation, lstm-snn-signal-generation-for-lgbm-features]
upstream: []
downstream: []
tags: [quant, microcap-swing, model-architecture]
pipeline_template: 
current_stage: 
pipeline_status: 
launch_mode: queued
---
## LSTM/SNN Signal Generation as LGBM Input Features

### Goal
Run LSTM and/or SNN models first, capture their probability outputs and hidden states, then feed these as additional features into the LGBM pipeline.

### Key Insight  
LGBM sees one moment through a multi-timeframe lens but has no sequential memory. LSTM/SNN hidden states encode trajectory information (momentum buildups, regime transitions in progress). Adding these as features gives LGBM temporal context it currently lacks.

### Implementation Plan
1. Train LSTM at 15m and 30m with walk-forward splits
2. Extract per-candle outputs: P(bear), P(chop), P(bull) + hidden state summary stats
3. Add as 6-9 new columns to LGBM feature matrix
4. Retrain LGBM with augmented features
5. Compare: augmented LGBM vs base LGBM vs pure LSTM
6. SNN variant: use firing rate and inter-spike intervals as features

### Leakage Prevention
- LSTM must be trained ONLY on data strictly before LGBM training window
- Each walk-forward fold needs nested temporal split: LSTM_train < LSTM_val < LGBM_train < LGBM_val
- This reduces effective training data - may need longer history

### Expected Outcome
- LGBM bull recall improvement (LSTM trajectory info helps spot approaching bull regimes)
- Marginal bear improvement (LGBM already good at bear)
- New feature importance: LSTM_P(bull) likely enters top 10
