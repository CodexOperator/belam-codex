---
primitive: task
status: open
priority: critical
created: 2026-03-25
owner: belam
depends_on: [quant-microcap-crypto-baseline]
upstream: [quant-baseline-v1]
downstream: []
tags: [snn, crypto, microcap, baseline, swing-trading, temporal]
pipeline_template: 
current_stage: 
pipeline_status: 
launch_mode: queued
---
# SNN Microcap Crypto Baseline

## Research Question
Does the SNN's event-driven spike processing extract signal from microcap cryptos that quant floor models cannot? The V1 baseline showed SNN beats LSTM on BTC (DM p=0.040) — does this advantage amplify on more volatile, less efficient microcap tokens?

## Scope
SNN and temporal neural models ONLY. Uses the quant task's data pipeline, features, and results as the floor to beat. Tests: LSTM → GRU → Leaky SNN → Synaptic SNN → Alpha SNN → Adaptive SNN.

## Depends On
`quant-microcap-crypto-baseline` — needs completed data pipeline and quant floor metrics as benchmark.

## Design

### Assets & Features
Same assets and feature sets as the quant task. Same multi-horizon targets (1, 5, 10, 20 candles).

### Delta Encoding Variants
The V1 notebook used a single delta encoding. Test exhaustively:

| Encoding | Description |
|----------|-------------|
| Delta-tanh (V1) | tanh(\|Δ\|) split pos/neg — baseline |
| Delta-scaled | tanh(\|Δ\| × s) with s ∈ [0.5, 1.0, 2.0, 5.0] |
| Rate coding | Direct Z-scored values as firing rates (no delta) |
| Population coding | N neurons per feature, Gaussian tuning curves |
| Temporal contrast | Current − exponential moving average (multi-scale τ) |

### Neuron Models (Exhaustive)

| Model | Library | Key Property |
|-------|---------|-------------|
| **Leaky (LIF)** | snntorch.Leaky | V1 baseline, exponential decay |
| **Synaptic** | snntorch.Synaptic | Two time constants (synaptic + membrane) — richer temporal filtering |
| **Alpha** | snntorch.Alpha | Alpha-function PSP — biologically realistic post-synaptic potential |
| **Recurrent Leaky** | snntorch.RLeaky | Recurrent connections in spiking layer |
| **Adaptive LIF (ALIF)** | Custom | Threshold adaptation — neurons become less responsive after firing, natural regime detection |
| **Izhikevich** | Custom | Richer dynamics (bursting, chattering, fast spiking modes) |

### Architecture Grid

| Config | Layer 1 | Layer 2 | Readout | Params (approx) |
|--------|---------|---------|---------|-----------------|
| Small | 48 | 24 | Mean membrane | ~2K |
| Medium | 128 | 64 | Mean membrane | ~10K |
| Large | 256 | 128 | Mean membrane | ~40K |
| Deep-Small | 64 → 32 → 16 | 3 layers | Weighted membrane | ~5K |
| Readout-Exp | 128 | 64 | Exponentially-weighted membrane | ~10K |
| Readout-Attn | 128 | 64 | Temporal attention over membrane states | ~12K |

### Sequence Lengths
V1 used T=20. Test: T ∈ [10, 20, 40, 80] — especially important for multi-candle prediction horizons. Match T to prediction horizon where possible.

### Training Variations

| Aspect | Options |
|--------|---------|
| Loss | HuberLoss(δ=0.01), MSE, Binary CE (for probability target) |
| β init | [0.5, 0.75, 0.9, 0.95] — test sensitivity to decay rate |
| Spike mode | Bernoulli (train) → deterministic (eval) vs deterministic always |
| Eval averaging | Single pass vs N=10 stochastic passes averaged |
| Patience | [15, 30, 50, 100] — grokking investigation (does late generalization appear?) |
| Scheduler | Cosine annealing vs ReduceLROnPlateau vs OneCycleLR |

### LSTM/GRU Baselines (Matched Capacity)
For every SNN config, train a matched-capacity LSTM and GRU:
- Same input encoding (delta or rate)
- Same parameter count (±10%)
- Same loss, optimizer, patience
- This is the comparability guarantee — any SNN win is architecture, not capacity

### Evaluation
Same metrics as quant task, plus:
- Diebold-Mariano test: SNN vs LSTM, SNN vs GRU, SNN vs best quant model
- Per-asset DM: does SNN advantage scale with volatility? (V1 hypothesis: BTC > SPY → microcaps > BTC?)
- β trajectory analysis: do learned decay rates differ by asset volatility?
- Spike rate analysis: are hidden layers producing meaningful patterns or saturating?
- Membrane potential distributions per regime (high-vol vs low-vol)
- Per-horizon analysis: does SNN advantage change with prediction horizon?

### Grokking Investigation
Run select configurations with patience=100+:
- Track test loss at epoch [15, 30, 50, 75, 100, 150]
- If improvement appears after epoch 50, this changes the entire training protocol
- Focus on SNN-Medium with T=40 on the most volatile microcap

## Acceptance Criteria
- [ ] All neuron model × architecture × encoding × horizon combinations tested
- [ ] LSTM/GRU baselines matched to every SNN configuration
- [ ] DM tests computed for all SNN vs LSTM comparisons per asset
- [ ] Volatility-scaling hypothesis tested: correlation between asset vol and SNN advantage magnitude
- [ ] Grokking investigation complete (patience=100+ runs)
- [ ] Best SNN config identified per asset per horizon
- [ ] Comparison table against quant floor from paired task
- [ ] Spike dynamics diagnostics (β evolution, spike rates, membrane distributions)
- [ ] Results exported to CSV + summary report

## Notes
- The key question is whether microcap volatility amplifies the SNN advantage seen on BTC in V1
- Do NOT optimize SNN hyperparams based on quant task results — independent search prevents information leak
- Adaptive LIF and Izhikevich neurons are custom implementations — may need debugging time
- If grokking is found, all other experiments should be rerun with updated patience
