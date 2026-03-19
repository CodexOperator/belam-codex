---
primitive: memory_log
timestamp: "2026-03-19T13:37:12Z"
category: technical
importance: 4
tags: [infrastructure, experiments, cpu, local-runner]
source: "session"
content: "Local CPU experiment runner works. run_local.py in machinelearning/snn_applied_finance/scripts/ runs all 81 equilibrium experiments on the 4-core ARM server without GPU. Full run: ~2.5 hours with --workers 1. Models small enough (nano-15 to medium-192) that GPU adds no real advantage. Dead neuron re-initialization added to SNNEquilibriumV2: Kaiming reinit for <1% spike rate neurons every 5 epochs after warmup, preserves sparsity masks. torch.nn.Buffer requires .fill_() not direct float assignment. Results save to notebooks/local_results/ with incremental saves and --resume support. Saves Colab Pro hours for tasks that don't need GPU."
status: consolidated
---

# Memory Entry

**2026-03-19T13:37:12Z** · `technical` · importance 4/5

Local CPU experiment runner works. run_local.py in machinelearning/snn_applied_finance/scripts/ runs all 81 equilibrium experiments on the 4-core ARM server without GPU. Full run: ~2.5 hours with --workers 1. Models small enough (nano-15 to medium-192) that GPU adds no real advantage. Dead neuron re-initialization added to SNNEquilibriumV2: Kaiming reinit for <1% spike rate neurons every 5 epochs after warmup, preserves sparsity masks. torch.nn.Buffer requires .fill_() not direct float assignment. Results save to notebooks/local_results/ with incremental saves and --resume support. Saves Colab Pro hours for tasks that don't need GPU.

---
*Source: session*
*Tags: infrastructure, experiments, cpu, local-runner*
