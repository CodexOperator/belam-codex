---
primitive: lesson
date: 2026-03-19
source: V2 deep analysis — continuous vs spike input comparison across all model variants
confidence: high
project: snn-applied-finance
tags: [snn, encoding, input-mode]
applies_to: [snn-applied-finance]
promotion_status: exploratory
doctrine_richness: 0
contradicts: []
---

# Continuous Input Mode Consistently Outperforms Spike Mode

Across all V2 model variants (SNN and LSTM, all schemes, all sizes), passing raw Gaussian activation values (continuous mode) to the SNN outperforms Bernoulli-sampled spike trains (spike mode).

**Why:** Bernoulli sampling introduces stochastic noise that destroys information. For a population-coded neuron with activation 0.7, continuous mode preserves the exact value; spike mode randomly fires (70%) or doesn't (30%) each timestep. Over T=20 steps, the spike count approximates the activation but with binomial noise — unnecessary information loss.

**Implication:** For financial SNN architectures, use continuous (graded) input by default. Reserve true spiking input for neuromorphic hardware deployment where it's required. Deterministic evaluation (continuous mode) is essential for reliable metrics — stochastic eval makes all accuracy and Sharpe measurements unreliable.

**Exception:** The equilibrium/streaming architecture may benefit from true spikes if the network has enough temporal steps to average out the noise (T >> 20).
