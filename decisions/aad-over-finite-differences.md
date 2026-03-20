---
primitive: decision
status: accepted
date: 2026-03-15
context: Production Quant Handbook — Greeks computation for any derivatives pricing work
alternatives: [analytical closed-form, finite differences (bumping), AAD]
rationale: AAD computes all first-order Greeks in ≤4× forward cost vs O(N) for bumping — up to 1,000× faster for large portfolios. PyTorch autograd gives 20% overhead for delta+vega vs 500%+ for finite diff. JAX jax.grad for GPU-native workflows.
consequences: [Use PyTorch autograd or JAX for all Greeks computation, Finite differences only as validation/debugging tool]
project: snn-applied-finance
tags: [derivatives, greeks, infrastructure]
upstream: [lessons/always-back-up-workspace-to-github]
---

# AAD Over Finite Differences for Greeks

No contest. Adjoint Algorithmic Differentiation is O(1) vs O(N) scaling. Use PyTorch autograd or JAX.
