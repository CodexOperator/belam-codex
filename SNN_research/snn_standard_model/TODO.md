# SNN Standard Neuron Model Research — To-Do List

## Status Key
- [ ] Not started
- [~] In progress
- [x] Complete

## Context

This to-do list covers **Part I: Standard Neuron Model Research** from the SNN Research Document v1.0. The goal is systematic benchmarking of snnTorch neuron models (Leaky, Synaptic, Alpha) on MNIST-family datasets to build intuition, establish baselines, and develop a reusable experimental pipeline. All work uses the `snntorch` library with PyTorch.

Reference files in this project: `dependencies`, `variables`, `two-neuron-trial`, `plotting-settings`, `training_spikes_MNIST.py`, `training_spikes_loop.py`.

---

## Phase 1 — Foundations: Leaky Neuron on Static MNIST

### Task 1.1: Implement the Experiment Infrastructure [~]
- [ ] `ExperimentConfig` and `ExperimentResult` dataclasses
- [ ] Reusable training loop function
- [ ] Metrics recording: accuracy, spike density, membrane stats, loss/accuracy curves, timing, learned params
- [ ] JSON save/load with naming convention `{experiment_id}_{neuron_model}_{dataset}_{timestamp}.json`
- [ ] Cross-experiment comparison utility

### Task 1.2: Leaky Beta Sweep — Rate Coding [ ]
- Beta values: `[0.5, 0.7, 0.8, 0.9, 0.95, 0.99]`
- Num steps: `[25, 50, 100]`
- Architecture: FC 784→1000→10 with Leaky neurons
- Dataset: Static MNIST, rate coding
- Batch: 128, LR: 5e-4, Adam, CrossEntropyLoss
- 1 epoch initial, 10 epochs for best configs

### Task 1.3: Leaky Beta Sweep — Latency Coding [ ]
- Best beta(s) from 1.2
- Tau values: `[1, 2, 5, 10, 20]`
- Test both exponential and linear latency coding
- Compare rate vs latency performance

### Task 1.4: Threshold Sensitivity Sweep [ ]
- Thresholds: `[0.5, 0.75, 1.0, 1.25, 1.5, 2.0]`
- Best beta + encoding from 1.2-1.3

### Task 1.5: Reset Mechanism Comparison [ ]
- Mechanisms: `"subtract"`, `"zero"`, `"none"`
- Best beta, encoding, threshold

### Task 1.6: Learnable Beta Experiment [ ]
- `learn_beta=True`, track evolution per epoch per layer
- Compare to best fixed-beta config

### Task 1.7: Inhibition Mode Experiment [ ]
- `inhibition=True`, compare to standard mode

---

## Phase 2 — Second-Order Models: Synaptic Neuron on Static MNIST

### Task 2.1: Alpha-Beta Interaction Grid Sweep [ ]
- Alpha: `[0.5, 0.7, 0.85, 0.9, 0.95]`
- Beta: `[0.5, 0.7, 0.85, 0.9, 0.95]`
- Best encoding/num_steps from Phase 1
- Record synaptic current distributions + temporal response profiles

### Task 2.2: Learnable Alpha and Beta [ ]
- `learn_alpha=True`, `learn_beta=True`
- Track co-evolution, per-layer learned values per epoch

### Task 2.3: Alpha → 0 Limit Verification [ ]
- Verify Synaptic(alpha=0) ≈ Leaky(same beta)
- Check if learnable alpha drifts to 0 on MNIST

### Task 2.4: Synaptic vs Leaky on Latency-Coded Inputs [ ]
- Compare best Leaky vs best Synaptic on latency-coded MNIST

---

## Phase 3 — Alpha Neuron and Cross-Model Comparisons

### Task 3.1: Alpha Neuron Baseline [ ]
### Task 3.2: Temporal Kernel Visualization [ ]
### Task 3.3: Alpha with Learnable Parameters [ ]
### Task 3.4: Three-Way Model Comparison [ ]
### Task 3.5: Extend to Fashion-MNIST [ ]

---

## Phase 4 — Neuromorphic Data

### Task 4.1: Best Leaky Config on N-MNIST [ ]
### Task 4.2: Best Synaptic Config on N-MNIST [ ]
### Task 4.3: Native vs Encoded Performance Analysis [ ]

---

## Visualization Tasks

### Task V1: Single-Neuron Dynamics Visualizations [ ]
### Task V2: Multi-Layer Spike Raster Visualizations [ ]
### Task V3: Output Spike Count Histograms and Animations [ ]
### Task V4: Membrane Potential Trace Overlays [ ]
### Task V5: Hyperparameter Landscape Heatmaps [ ]
### Task V6: Comparative Loss and Accuracy Curves [ ]
### Task V7: Spike Density Distribution Analysis [ ]

---

## Progress Report

### Task R1: Generate Comprehensive Progress Report [ ]

---

## Execution Notes
- **Priority**: Task 1.1 → Phase 1 → 2 → 3 → 4. Viz alongside phases. Report last.
- **Deps**: snntorch, torch, numpy, matplotlib, pandas, seaborn, tonic ✅ installed
- **GPU**: Use CUDA if available
- **Seeds**: `torch.manual_seed(42)`, `np.random.seed(42)`
- **Dirs**: `experiments/`, `plots/`, `reports/`, `checkpoints/`
