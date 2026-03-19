---
primitive: lesson
date: 2026-03-19
source: V2 and V3 critique reviews — statistical methodology gaps
confidence: high
project: snn-applied-finance
tags: [methodology, statistics, validation]
applies_to: [snn-applied-finance]
---

# Per-Fold Significance Tests and Permutation Tests Are Required

Pooled accuracy can hide regime-dependent signal. V2's 54.02% pooled accuracy is statistically significant vs majority baseline (z≈3.25, p≈0.0006), but if Fold 1 drives most of the signal (57% vs 52% in other folds), pooled significance is misleading.

**Two required tests before claiming signal:**

1. **Per-fold significance tests against fold-specific majority baseline.** Each fold has different class balance — test each fold's accuracy individually. With ~1,500 samples per fold, minimum detectable effect at p<0.05 is ≈ ±2.1pp.

2. **Permutation tests for specialist F1 claims.** Shuffle time-ordered labels within each fold 1000× to get empirical null distribution of F1. Accounts for temporal structure that theoretical random-baseline calculations miss. Critical for rare-event detectors (CrashDetector at 4.5% event rate) where small sample sizes make bootstrap CIs wide.

**Why this matters:** V3's RallyDetector F1 lift of +0.023 is within one standard deviation of the bootstrap estimate — likely not significant. VolSpikeDetector's lift/std ≈ 3.8 is more credible. Without proper tests, we risk building on noise.
