---
title: SNN Deep Analysis — Standard Model Synaptic & Alpha
status: in_pipeline
priority: high
tags: snn, research, analysis, deep-dive, standard-model
pipeline: snn-deep-analysis-standard-synaptic-alpha
project: snn-applied-finance
depends_on: [snn-deep-analysis-standard-leaky]
created: 2026-03-31
---

# SNN Deep Analysis — Standard Model Synaptic & Alpha

Deep research analysis of the standard model Synaptic and Alpha neuron experiments on MNIST/FashionMNIST.

## Scope

Analyze Synaptic and Alpha neuron experiments:
- `machinelearning/snn_standard_model/experiment_infrastructure.py` — model building for Synaptic/Alpha (dual decay constants)
- `machinelearning/snn_standard_model/experiments/syn*_*.json` — 22 Synaptic MNIST + 3 FashionMNIST experiments
- `machinelearning/snn_standard_model/experiments/alpha*_*.json` — 13 Alpha MNIST + 3 FashionMNIST experiments (41 total)

## Deliverables

1. **Cost function analysis** — Same CrossEntropyLoss on summed membrane, but now with TWO decay constants (alpha + beta). What each controls. How they interact. Whether learn_alpha/learn_beta are used.
2. **Encoding deep dive** — How Synaptic neurons differ from Leaky: synaptic current as intermediate state. The Alpha neuron's excitatory/inhibitory synaptic model. Exact membrane equations for both vs Leaky.
3. **Neuron communication** — Synaptic: pre-spike → synaptic current (alpha decay) → membrane potential (beta decay). Alpha: excitatory + inhibitory synaptic pathways. Visualize the dual-timescale dynamics.
4. **Network topology** — Same 784→1000→10 but with Synaptic/Alpha neurons. How the extra state variables change information capacity and temporal dynamics vs Leaky.
5. **Experiment results** — Alpha-beta sweep heatmaps from actual JSON results. Compare Leaky vs Synaptic vs Alpha accuracy across matched configs. FashionMNIST transfer analysis.
6. **Cross-neuron comparison** — Direct comparison with Leaky results from the previous analysis. Which neuron type wins and why.

## Reference Material

Same infrastructure as Leaky analysis, plus results from the Leaky analysis at:
`machinelearning/snn_standard_model/research/deep_analysis/leaky_lif/`

## Output Location

All scripts and outputs go to: `machinelearning/snn_standard_model/research/deep_analysis/synaptic_alpha/`
