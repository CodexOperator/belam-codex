---
primitive: task
status: open
priority: critical
created: 2026-03-25
owner: belam
depends_on: [quant-cross-asset-stablecoin-spreads]
upstream: [quant-baseline-v1]
downstream: []
tags: [snn, cross-asset, stablecoin, arbitrage, spreads, temporal]
---

# SNN Cross-Asset & Stablecoin Spread Models

## Research Question
Can SNN spike dynamics detect spread regime transitions and Poisson-distributed depeg events faster than conventional quant models? The SNN's change-detection inductive bias maps naturally to spread deviations — every spread move away from equilibrium is a "spike" event.

## Scope
SNN and temporal models on spread/basis dynamics. Uses quant task's data pipeline and results as floor.

## Design

### Unique SNN Angle: Spread-as-Spike Encoding
Instead of delta-encoding price features, encode the **spread deviation itself** as a spike signal:
- Spread > threshold → excitatory spike (deviation detected)
- Spread velocity > threshold → rate-coded urgency signal
- This is a natural fit: biological neurons detect deviations from homeostasis, spreads ARE deviations from equilibrium

### Neuron Model Focus
- **Adaptive LIF** — threshold adaptation creates natural "alert fatigue" → fresh sensitivity after calm periods
- **Synaptic** — dual time constants can capture fast spread moves (short τ) vs regime shifts (long τ)
- All standard models (Leaky, Alpha, RLeaky) for comparison

### Multi-Scale Temporal Processing
Stablecoin spreads revert on different timescales:
- Seconds-minutes: DEX arbitrage bots (not our horizon)
- Hours: CEX settlement, institutional rebalancing — **our target**
- Days: Structural trust/yield differentials

Test SNN with multi-scale T: [10, 20, 50, 100] on 1h candles

### Hawkes Process Integration
Self-exciting events (one depeg increases probability of another — contagion). Model as Hawkes process and use the intensity function as an SNN input feature:
```
λ(t) = μ + Σ α·exp(-β(t - tᵢ)) for all past events tᵢ
```
The SNN should learn whether to amplify or dampen the Hawkes signal.

### Evaluation
Same as quant task plus:
- DM tests: SNN vs LSTM vs best quant model on each spread type
- Event detection latency: how many candles before the model detects a depeg/spread widening?
- False positive rate on depeg alerts
- Regime transition detection speed: SNN vs rolling correlation methods

## Acceptance Criteria
- [ ] Spread-as-spike encoding implemented and compared to standard delta encoding
- [ ] All neuron models tested on all three sub-modules
- [ ] Hawkes process features integrated
- [ ] DM tests against quant floor
- [ ] Event detection latency analysis
- [ ] Results exported + summary report
