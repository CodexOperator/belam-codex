---
topic: SNN Architecture Patterns
tags: [alpha, leaky, membrane, neuron, potential, snntorch, spike, synaptic]
created: 2026-03-17
updated: 2026-03-17
sources: [lessons/beta-convergence-is-market-determined.md, lessons/breakeven-accuracy-before-building.md, lessons/confident-abstention-is-signal.md, lessons/event-detection-not-state-classification.md, lessons/snn-treats-like-weird-cnn.md, lessons/tiny-snn-gpu-parallelism.md]
related: [experiment-methodology, financial-encoding, research-workflow]
---

# SNN Architecture Patterns

## Key Findings

- Confidence thresholding (trade top-30% signals only) *(lessons/breakeven-accuracy-before-building.md)*
- Daily resolution (breakeven drops to ~55.1%) *(lessons/breakeven-accuracy-before-building.md)*
- Maker orders (0.02% cost → breakeven ~50.7%) *(lessons/breakeven-accuracy-before-building.md)*
- Always calculate the minimum accuracy required for profitability at your target resolution and cost structure BEFORE committing to a model architecture. *(lessons/breakeven-accuracy-before-building.md)*
- 50-neuron specialist micro-networks show genuine signal for event detection (CrashDetector, RallyDetector, VolSpikeDetector) but fail completely for state classification (SidewaysDetector, TrendFollower). *(lessons/event-detection-not-state-classification.md)*
- Root cause: T=20 temporal window insufficient for sustained-state detection. Events are transient spikes — perfect for SNN change-detection. States require persistent temporal context beyond the window. *(lessons/event-detection-not-state-classification.md)*
- Static window encoding (batch of features → spike pattern → classify) wastes the SNN's temporal advantage completely. V1 collapsed to majority-class because rate coding on 1h candles gave the SNN nothing a logistic regression couldn't do. *(lessons/snn-treats-like-weird-cnn.md)*
- SNNs are fundamentally change-detectors, not classifiers. Use them for what they're good at. *(lessons/snn-treats-like-weird-cnn.md)*
- 5. **Explicit cleanup:** `del model` + `gc.collect()` + `torch.cuda.empty_cache()` after every fold. Without this, VRAM climbs ~50-100MB per experiment and never comes back. *(lessons/tiny-snn-gpu-parallelism.md)*
- **fp16/mixed precision:** BCELoss produces NaN/Inf under autocast. Models are too small to benefit anyway. *(lessons/tiny-snn-gpu-parallelism.md)*
- **Conservative worker counts:** 3-6 workers on a T4 leaves >60% of GPU idle between kernel launches. *(lessons/tiny-snn-gpu-parallelism.md)*
- **Relying on Python GC alone:** PyTorch's CUDA caching allocator holds memory even after Python objects are collected. Must explicitly call `torch.cuda.empty_cache()`. *(lessons/tiny-snn-gpu-parallelism.md)*

## Notes

*(Add contextual notes here as patterns emerge)*

## See Also

- [→ Daily 2026-03-17](../memory/2026-03-17.md)
