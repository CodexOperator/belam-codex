---
primitive: lesson
status: superseded
date: 2026-03-16
source: v4 notebook GPU profiling (Shael observed 2GB steady climb)
confidence: high
project: snn-applied-finance
tags: [gpu, parallelism, performance, infrastructure]
applies_to: [pipeline-template, v4, v5+]
superseded_by: gpu-parallel-thrashing-t4
promotion_status: exploratory
doctrine_richness: 10
contradicts: []
---

# Tiny SNN Models Need GPU Throughput Optimization, Not Memory Caution

## Context
V4 notebook runs 32+ experiments with models ranging from 5 to 192 neurons (<1MB VRAM each). Initial parallel worker counts were conservative (T4: 3→8), batch sizes small (256→1024), and no GPU memory management existed.

## Finding
For sub-1MB models, the GPU bottleneck is **compute saturation**, not memory. Conservative parallelism wastes most of the GPU's capacity. Meanwhile, without explicit cleanup, PyTorch's caching allocator accumulates dead tensors and VRAM climbs monotonically even though active memory is tiny.

## ⚠️ SUPERSEDED: Worker Count Advice

~~Original advice suggested 12 workers on T4.~~ **Actual benchmarking proved this wrong.** See `gpu-parallel-thrashing-t4` for the corrected findings.

## What Works (Updated)
1. **2 parallel workers on T4, not more.** Scaling past 2 *degrades* throughput due to Python GIL contention and CUDA stream synchronization thrashing. Benchmarked: 12 workers was slower than 2.
2. **Batch size 4096** is the real throughput lever. Going 512→4096 gave 3.6× speedup. This matters far more than worker count.
3. **Prefetch data to GPU once:** `prefetch_to_gpu()` eliminates thousands of redundant CPU→GPU tensor copies across folds × experiments.
4. **Pin memory + persistent workers:** `pin_memory=True`, `num_workers=2`, `persistent_workers=True` on DataLoaders for async transfer.
5. **Explicit cleanup OUTSIDE loops:** `del model` + `gc.collect()` + `torch.cuda.empty_cache()` after the loop completes, not inside it. `empty_cache()` inside loops acts as a global barrier that kills parallelism.

## Production Config (T4)
```python
batch_size = 4096
n_parallel = 2
# torch.cuda.empty_cache() ONLY at end of cell, after loop completes
```

## What Doesn't Work
- **fp16/mixed precision:** BCELoss produces NaN/Inf under autocast. Models are too small to benefit anyway.
- **12+ workers on T4:** GIL contention on CPU-side tensor slicing makes more threads counterproductive.
- **Relying on Python GC alone:** PyTorch's CUDA caching allocator holds memory even after Python objects are collected. Must explicitly call `torch.cuda.empty_cache()`.
- **`gpu_cleanup()` inside hot loops:** Acts as a global synchronization barrier across all threads.

## Key Insight
The optimal GPU strategy depends on **model size relative to GPU capacity**, not just GPU type. For tiny models (<1MB), maximize **batch size first**, then use **minimal parallelism** (2 workers) to overlap CPU prep with GPU compute. More Python threads ≠ more GPU throughput when the GIL makes CPU-side prep sequential.
