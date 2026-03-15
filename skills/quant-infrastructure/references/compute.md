# GPU/TPU Compute Reference

## Hardware Selection Matrix

| Hardware | VRAM | Best For | Batch Size |
|----------|------|----------|------------|
| H100 | 80GB | Largest models, FP8/torch.compile | 2048+ |
| A100 | 40-80GB | BF16, TF32 auto | 1024+ |
| L4 | 24GB | Ada Lovelace, FP16/INT8 | 512-1024 |
| T4 | 16GB | FP16, architecture search | 256-512 |
| V100 | 16GB | FP16, standard training | 256-512 |
| TPU v6e-1 | HBM | XLA-compiled batch parallelism | 1024+ |

## GPU Optimizations

- **H100 FP8:** `torch.float8_e4m3fn` for extreme throughput. SNN spike ops are naturally low-precision-friendly.
- **A100/H100 torch.compile():** JIT-compile training loops. 1.5–3× speedup on temporal unrolling.
- **A100/H100 BF16:** Preferred over FP16 — no loss scaling needed, wider dynamic range.
- **TF32 (Ampere+):** Auto-enabled, free 3× matmul speedup.
- **Flash Attention 2 (H100):** O(n) memory for attention layers.

## TPU Optimizations

- **XLA graph compilation:** Requires static graph shapes. SNN timestep loops must be traced/compiled, not dynamic.
- **Batch parallelism:** `torch_xla.distributed` for multi-core splits.
- **Padding:** TPU requires uniform-length spike tensors.

## Cross-Hardware Strategies

- **Batch size scaling rule:** Double batch → multiply LR by √2
- **Gradient accumulation:** Simulate large batches on smaller GPUs
- **Multi-epoch on large hardware:** Run 50+ epochs where CPU ran 1
- **Profiling:** `torch.profiler` to find bottlenecks (temporal unrolling vs matmuls vs spike ops)

## Monte Carlo GPU Benchmarks

- CUDA barrier option pricing: 25ms GPU vs 13,530ms CPU (537× speedup)
- 5M paths, 365 steps
- PyTorch: `torch.randn(N_paths, N_steps, device='cuda')` + autograd for free Greeks
- CuPy and Numba CUDA JIT: near-native CUDA with Python syntax
- Path counts: 100K–1M vanilla Europeans, 1M–10M path-dependent exotics
