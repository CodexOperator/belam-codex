---
type: lesson
id: gpu-parallel-thrashing-t4
title: "GPU parallel worker thrashing on Tesla T4 with Python threads"
status: active
learned: 2026-03-16
source: v4-notebook-benchmarking
confidence: high
tags: [gpu, parallelism, performance, colab, t4]
related: [beta-convergence, snn-treats-like-weird-cnn]
supersedes: tiny-snn-gpu-parallelism
promotion_status: exploratory
doctrine_richness: 5
contradicts: []
---

# GPU Parallel Worker Thrashing on Tesla T4

## Context
V4 notebook threaded workflow ran slower than expected with `batch_size=2048` and 12 concurrent workers on Tesla T4.

## Findings

1. **Optimal workers = 2, not more.** Scaling past 2 workers *degrades* throughput (236s → 271s at 12 workers) due to:
   - Python GIL contention on CPU-bound tensor slicing
   - CUDA stream synchronization thrashing the GPU scheduler
   - Thread coordination overhead exceeds parallelism gains

2. **Batch size is the real throughput lever.** Going from 512 → 4096 cut execution time from 603.60s → 166.68s (3.6× speedup), throughput 0.03 → 0.11 fold-runs/sec.

3. **Shuffle overhead is negligible (~6%).** `shuffle=True` on pre-fetched GPU `TensorDataset` causes minor host-device sync cost — acceptable for training correctness.

4. **`gpu_cleanup()` inside loops is a global barrier.** Frequent `torch.cuda.empty_cache()` calls inside fold-iteration loops synchronize all threads, killing parallelism. Moving cleanup to after the loop → 162.32s final time.

## Production Config
```python
batch_size = 4096
n_parallel = 2
# torch.cuda.empty_cache() ONLY at end of cell, after loop completes
```

## Principle
More Python threads ≠ more GPU throughput. The GIL makes CPU-side prep sequential regardless of thread count. Maximize batch size first, then use minimal parallelism (2 workers) to overlap CPU prep with GPU compute. Keep global barriers (cache clearing, synchronization) outside hot loops.
