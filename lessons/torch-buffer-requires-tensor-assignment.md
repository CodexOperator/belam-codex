---
primitive: lesson
date: 2026-03-19
source: build-equilibrium-snn pipeline, Shael experiment run
confidence: high
tags: [snn, pytorch, debugging]
promotion_status: candidate
doctrine_richness: 8
contradicts: []
---

# torch.nn.Buffer Requires Tensor Assignment, Not Float

## Context

The `SNNEquilibriumV2` model's `set_threshold()` method performs threshold annealing — linearly ramping LIF neuron thresholds from 0.2 → 1.0 over the first 50% of training epochs.

## What Happened

`set_threshold()` assigned a plain Python float directly to `lif.threshold`:
```python
lif.threshold = threshold  # TypeError!
```
Since `threshold` was registered as a `torch.nn.Buffer`, PyTorch raises `TypeError: cannot assign 'float' as buffer 'threshold' (torch.nn.Buffer, torch.Tensor or None expected)`. This crashed every SNN experiment that used threshold annealing — the same error repeated across all folds and configs.

## Lesson

**Never assign a raw Python scalar to a `torch.nn.Buffer`.** Use in-place tensor operations: `.fill_()`, `.copy_()`, or `torch.tensor()` wrapping.

## Application

When writing or reviewing any code that modifies registered buffers (thresholds, betas, running stats), always use tensor-safe operations:
```python
# ✅ Correct
lif.threshold.fill_(threshold)
lif.threshold.copy_(torch.tensor(threshold))

# ❌ Wrong
lif.threshold = threshold  # float
lif.threshold = 1.0        # float
```

This applies to all `register_buffer()` parameters across SNN models — not just thresholds. Builders should treat buffer modification the same as parameter modification: always tensor ops.
