---
primitive: task
status: in_pipeline
priority: high
owner: builder
tags: [snn, ensemble, specialists]
project: snn-applied-finance
estimate: 4h
depends_on: []
version_label: v5-stacking
---

# Stack Specialist Micro-Networks

Combine CrashDetector + RallyDetector + VolSpikeDetector via logistic regression combiner. NOT another SNN — keep the stacking layer simple.

## Steps
1. Check correlation matrix of specialist predictions (independence determines ensemble value)
2. Use Fold 3 as exclusive stacking test (avoid data leakage)
3. Precision-recall curves (4.5% event rate → ROC uninformative)
4. Bootstrap CI for F1 lift claims

## References
- [[event-detection-not-state-classification]]
- V3 specialist results in TECHNIQUES_TRACKER.md
