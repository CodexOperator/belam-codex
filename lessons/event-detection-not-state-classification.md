---
primitive: lesson
date: 2026-03-15
source: V3 specialist micro-network results
confidence: high
project: snn-applied-finance
tags: [snn, specialists, architecture]
applies_to: [snn-applied-finance]
---

# Simple SNNs Detect Events, Not States

50-neuron specialist micro-networks show genuine signal for event detection (CrashDetector, RallyDetector, VolSpikeDetector) but fail completely for state classification (SidewaysDetector, TrendFollower).

Root cause: T=20 temporal window insufficient for sustained-state detection. Events are transient spikes — perfect for SNN change-detection. States require persistent temporal context beyond the window.

Fix: Equilibrium SNN with persistent state, or longer temporal windows for state-detection specialists.
