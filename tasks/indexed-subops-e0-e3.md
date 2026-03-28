---
primitive: task
status: open
priority: high
created: 2026-03-24
owner: belam
depends_on: [t31, t34, t8]
upstream: [persistent-extend-and-indexed-subops]
downstream: []
tags: [quant, microcap-swing, model-architecture]
project: codex-engine
---

## Iterative Model Improvement Loop Architecture

### Goal
Design a systematic loop that chains specialist stacking, teacher-student distillation, and signal generation into a self-improving research pipeline.

### Architecture
```
Loop N:
  1. Base models (LGBM, LSTM) produce predictions
  2. High-confidence outputs become teacher labels
  3. Student models (ANN/SNN) train on teacher labels  
  4. Student outputs become new features for base models
  5. Retrain base models with augmented features
  6. Ensemble all models with updated stacking
  7. Measure: did overall lift improve? If yes, loop N+1
```

### Convergence Criteria
- Lift improvement < 0.1% between iterations → stop
- Max 5 iterations (diminishing returns expected)
- Walk-forward validation at every step (no leakage)

### Implementation Notes
- Each iteration needs fresh walk-forward splits
- Track feature importance evolution across iterations
- Log which model type contributes most per iteration
- Risk: overfitting cascade - each loop adds complexity
- Mitigation: holdout test set never touched during loop

### Dependencies
- t31 (specialist stacking) — provides the ensemble framework
- t34 (teacher-student) — provides the distillation step
- t8 (signal generation) — provides the feature augmentation step
- All three must work individually before chaining

### Research Value
- Proves/disproves whether iterative stacking converges or diverges
- Identifies the information ceiling for this feature set
- Maps which model architectures contribute unique signal
