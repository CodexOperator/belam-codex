---
topic: Research Workflow
tags: [commit, consolidat, decision, document, insight, knowledge, lesson, memory]
created: 2026-03-17
updated: 2026-03-17
sources: [lessons/breakeven-accuracy-before-building.md, lessons/tiny-snn-gpu-parallelism.md]
related: [experiment-methodology, financial-encoding, snn-architecture]
---

# Research Workflow

## Key Findings

- Confidence thresholding (trade top-30% signals only) *(lessons/breakeven-accuracy-before-building.md)*
- Daily resolution (breakeven drops to ~55.1%) *(lessons/breakeven-accuracy-before-building.md)*
- Maker orders (0.02% cost → breakeven ~50.7%) *(lessons/breakeven-accuracy-before-building.md)*
- Always calculate the minimum accuracy required for profitability at your target resolution and cost structure BEFORE committing to a model architecture. *(lessons/breakeven-accuracy-before-building.md)*
- 5. **Explicit cleanup:** `del model` + `gc.collect()` + `torch.cuda.empty_cache()` after every fold. Without this, VRAM climbs ~50-100MB per experiment and never comes back. *(lessons/tiny-snn-gpu-parallelism.md)*
- **fp16/mixed precision:** BCELoss produces NaN/Inf under autocast. Models are too small to benefit anyway. *(lessons/tiny-snn-gpu-parallelism.md)*
- **Conservative worker counts:** 3-6 workers on a T4 leaves >60% of GPU idle between kernel launches. *(lessons/tiny-snn-gpu-parallelism.md)*
- **Relying on Python GC alone:** PyTorch's CUDA caching allocator holds memory even after Python objects are collected. Must explicitly call `torch.cuda.empty_cache()`. *(lessons/tiny-snn-gpu-parallelism.md)*

## Notes

*(Add contextual notes here as patterns emerge)*

## See Also

- [→ Daily 2026-03-17](../memory/2026-03-17.md)
- [→ Daily 2026-03-19](../memory/2026-03-19.md)
- [→ Daily 2026-03-20](../memory/2026-03-20.md)
- [→ Daily 2026-03-21](../memory/2026-03-21.md)
