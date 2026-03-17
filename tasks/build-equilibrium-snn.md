---
primitive: task
status: blocked
priority: critical
owner: builder
tags: [snn, architecture, streaming]
project: snn-applied-finance
estimate: 1-2 days
depends_on: []
---

# Build Equilibrium SNN Architecture

Shael's novel architecture. Continuous spike streaming where the network maintains persistent state across candles. Opponent-coded UP/DOWN output neurons — firing rate gap = direction + conviction.

## Requirements
- No batch processing — streaming inference
- State persists across observations (no reset between candles)
- Tonic inputs (absolute features → base firing rates) + phasic bursts (delta features → change signals)
- Truncated BPTT for training (K=5-10 candles, detach at boundary)
- Warmup LR schedule (1e-6 → 1e-4 over 20 epochs before cosine annealing)
- Long patience (500+ epochs, patience=100+) to check for grokking

## References
- [[snn-treats-like-weird-cnn]]
- [[event-detection-not-state-classification]]
- TECHNIQUES_TRACKER.md → "Continuous Spike Streaming" section
