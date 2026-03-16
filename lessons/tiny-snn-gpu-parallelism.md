---
primitive: lesson
date: 2026-03-16
source: v4 notebook GPU profiling (Shael observed 2GB steady climb)
confidence: high
project: snn-applied-finance
tags: [gpu, parallelism, performance, infrastructure]
applies_to: [pipeline-template, v4, v5+]
---

# Tiny SNN Models Need Aggressive GPU Parallelism, Not Memory Caution

## Context
V4 notebook runs 32+ experiments with models ranging from 5 to 192 neurons (<1MB VRAM each). Initial parallel worker counts were conservative (T4: 3→8), batch sizes small (256→1024), and no GPU memory management existed.

## Finding
For sub-1MB models, the GPU bottleneck is **compute saturation**, not memory. Conservative parallelism wastes most of the GPU's capacity. Meanwhile, without explicit cleanup, PyTorch's caching allocator accumulates dead tensors and VRAM climbs monotonically even though active memory is tiny.

## What Works
1. **Push parallel workers hard:** T4: 12, A100: 20, H100: 24. These models are so small that dozens can coexist on any modern GPU.
2. **Large batch sizes:** 2048+ for tiny models. Reduces kernel launch overhead and fills GPU compute pipelines.
3. **Prefetch data to GPU once:** `prefetch_to_gpu()` eliminates thousands of redundant CPU→GPU tensor copies across folds × experiments.
4. **Pin memory + persistent workers:** `pin_memory=True`, `num_workers=2`, `persistent_workers=True` on DataLoaders for async transfer.
5. **Explicit cleanup:** `del model` + `gc.collect()` + `torch.cuda.empty_cache()` after every fold. Without this, VRAM climbs ~50-100MB per experiment and never comes back.

## What Doesn't Work
- **fp16/mixed precision:** BCELoss produces NaN/Inf under autocast. Models are too small to benefit anyway.
- **Conservative worker counts:** 3-6 workers on a T4 leaves >60% of GPU idle between kernel launches.
- **Relying on Python GC alone:** PyTorch's CUDA caching allocator holds memory even after Python objects are collected. Must explicitly call `torch.cuda.empty_cache()`.

## Key Insight
The optimal GPU strategy depends on **model size relative to GPU capacity**, not just GPU type. For tiny models (<1MB), maximize parallelism and throughput. For large models (>1GB), the opposite — minimize parallel copies and carefully manage memory. The V4 models are firmly in the "saturate the GPU" category.
