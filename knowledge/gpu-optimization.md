---
topic: GPU & Compute Optimization
tags: [a100, batch size, colab, cuda, fp16, mixed precision, throughput, training time]
created: 2026-03-17
updated: 2026-03-17
sources: [lessons/tiny-snn-gpu-parallelism.md]
related: []
---

# GPU & Compute Optimization

## Key Findings

- 5. **Explicit cleanup:** `del model` + `gc.collect()` + `torch.cuda.empty_cache()` after every fold. Without this, VRAM climbs ~50-100MB per experiment and never comes back. *(lessons/tiny-snn-gpu-parallelism.md)*
- **fp16/mixed precision:** BCELoss produces NaN/Inf under autocast. Models are too small to benefit anyway. *(lessons/tiny-snn-gpu-parallelism.md)*
- **Conservative worker counts:** 3-6 workers on a T4 leaves >60% of GPU idle between kernel launches. *(lessons/tiny-snn-gpu-parallelism.md)*
- **Relying on Python GC alone:** PyTorch's CUDA caching allocator holds memory even after Python objects are collected. Must explicitly call `torch.cuda.empty_cache()`. *(lessons/tiny-snn-gpu-parallelism.md)*

## Notes

*(Add contextual notes here as patterns emerge)*

## See Also

- [→ Daily 2026-03-17](../memory/2026-03-17.md)
