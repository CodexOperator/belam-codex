---
title: SNN Deep Analysis — Standard Model Leaky (LIF)
status: in_pipeline
priority: high
tags: snn, research, analysis, deep-dive, standard-model
pipeline: snn-deep-analysis-standard-leaky
project: snn-applied-finance
created: 2026-03-31
---

# SNN Deep Analysis — Standard Model Leaky (LIF)

Deep research analysis of the standard model Leaky (LIF) neuron experiments on MNIST/FashionMNIST.

## Scope

Analyze the standard model infrastructure and Leaky neuron experiments:
- `machinelearning/snn_standard_model/experiment_infrastructure.py` — core training loop, model building, encoding
- `machinelearning/snn_standard_model/experiment_plan.py` — experiment matrix
- `machinelearning/snn_standard_model/experiments/beta*_Leaky_*.json` — 29 rate-coded MNIST + 2 FashionMNIST + 20 latency-coded MNIST experiments (51 total)

## Deliverables

1. **Cost function analysis** — CrossEntropyLoss on summed membrane potentials (not spike counts like finance). What parameters vs hyperparameters. How beta/threshold/num_steps are varied across experiments.
2. **Encoding deep dive** — Rate coding (`spikegen.rate`) vs Latency coding (`spikegen.latency`). Exact math for both. Visualize the same MNIST digit encoded both ways. Show how tau and linear vs exponential latency affect spike timing.
3. **Neuron communication** — LIF (snn.Leaky) dynamics with `init_hidden=True`. How membrane potential accumulates over timesteps. How the output neuron uses summed membrane (not spike count) for classification.
4. **Network topology** — 784→1000→10 architecture. Rate vs latency input representation. Spike density and membrane statistics from actual experiment results.
5. **Experiment results visualization** — Beta sweep results, steps sweep, learned vs fixed beta comparison. Pull actual accuracy/loss curves from the 51 JSON result files.

## Reference Material

- Infrastructure code: `machinelearning/snn_standard_model/experiment_infrastructure.py`
- Experiment results: `machinelearning/snn_standard_model/experiments/` (JSON files with config + results)
- Reports: `machinelearning/snn_standard_model/reports/SNN_Progress_Report.md`
- Plots: `machinelearning/snn_standard_model/plots/`

## Output Location

All scripts and outputs go to: `machinelearning/snn_standard_model/research/deep_analysis/leaky_lif/`
