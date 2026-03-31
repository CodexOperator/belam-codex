---
primitive: lesson
date: 2026-03-19
source: stack-specialists pipeline — 15 experiments, 42 runs, full stacking evaluation
confidence: high
priority: high
tags: [snn, ensemble, stacking, architecture, dead-end]
promotion_status: exploratory
doctrine_richness: 10
contradicts: []
---

# Stacking Specialist Micro-Networks Is a Dead End

## The Finding

Combining three event-detection SNN specialists (CrashDetector, RallyDetector, VolSpikeDetector) via logistic regression stacking **does not produce a useful direction predictor.** The shuffled-labels null model (50.55% accuracy, -0.62 Sharpe) is statistically indistinguishable from the best real stacker (51.93%, -0.84 Sharpe). Every real experiment has negative net Sharpe.

## Why It Fails — Three Structural Problems

1. **Specialist predictions lack diversity.** Max correlation = 0.671 — all three specialists see the same 7 delta-encoded features and make overlapping predictions. Information-theoretic gain from combining correlated predictors is minimal.

2. **Event detection ≠ direction prediction.** Detecting that a crash *happened* (retrospective) ≠ predicting the next candle will go down (prospective). The stacker tries to bridge this gap but the information content is too low.

3. **Feature space is too impoverished.** Six features (3 probabilities + 3 entropies) from weak specialists (AUC 0.56-0.67) ≈ 10 parameters in the LR stacker. Compare: V3 Scheme B monolithic SNN has 14 delta-encoded features processed through 12K parameters of temporal dynamics.

## Key Evidence

- VolSpikeDetector has highest individual AUC (0.656) but is direction-agnostic — using it alone (49.74%) is worse than majority baseline
- Crash+Rally together (50.93%) ≈ full stacker without VolSpike — vol spikes don't predict direction
- Abstention produces zero coverage in 12/15 experiments — stacker probabilities are clustered near 0.5
- The V3 Scheme B reference (52.0%, +0.45 Sharpe) is strictly superior to all stacking variants

## The Principle

Composition at the **prediction level** (stacking probabilities) doesn't work when individual detectors are weak and correlated. Composition should happen at the **architectural level** (multi-scale temporal layers within a single SNN).

## What To Do Instead

Invest in monolithic approaches: Scheme B validation, equilibrium SNN with membrane readout. These preserve temporal context and produce natural abstention signals that stacking cannot replicate.
