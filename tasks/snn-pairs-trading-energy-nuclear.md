---
primitive: task
status: open
priority: critical
created: 2026-03-25
owner: belam
depends_on: [quant-pairs-trading-energy-nuclear]
upstream: []
downstream: []
tags: [snn, pairs-trading, energy, nuclear, temporal, jump-detection]
---

# SNN Pairs Trading: Energy & Nuclear Indices

## Research Question
Can an SNN's spike dynamics detect Poisson-distributed jump events and mean-reversion timing in energy/nuclear pair spreads better than conventional quant models? The SNN's biological analogy — neurons detecting homeostatic deviations — maps directly to spread trading.

## Scope
SNN and temporal models on pair spread dynamics. Uses quant task's cointegrated pairs, OU parameters, and feature sets as floor.

## Design

### Core Hypothesis: Spike = Jump
In the OU + Poisson framework, jumps are exactly what biological neurons are designed to detect — sudden deviations from baseline. The SNN should naturally excel at:
1. **Jump detection:** Is this spread move a Poisson jump (don't trade) or an OU deviation (trade)?
2. **Reversion timing:** Given a deviation, when will mean-reversion accelerate?
3. **Regime classification:** Is the spread currently in OU regime (tradeable) or jump regime (dangerous)?

### Encoding Design

**Spread-native encoding:**
- Spread Z-score → rate coding (continuous input proportional to deviation magnitude)
- Spread velocity → delta encoding (change detection)
- Jump indicator → binary spike input (1 when jump detected by Lee-Mykland)
- OU residual → deviation from model prediction as continuous input

**Multi-channel architecture:**
Channel 1: Spread dynamics (Z-score, velocity, acceleration) — 6 features
Channel 2: Market context (VIX, uranium spot, rates) — 4 features  
Channel 3: Jump features (Poisson λ, bipower variation, jump magnitude) — 4 features
Total: 14 input channels (same as V1 by coincidence — good for architecture reuse)

### Neuron Models
- **Adaptive LIF** — threshold adaptation after jump events creates natural "cooldown" (don't re-enter immediately after a jump)
- **Synaptic** — dual τ captures fast reversion (hours) vs slow regime shifts (weeks)
- **Leaky (baseline)** — standard comparison
- **LSTM/GRU** — matched capacity baselines

### Architecture Configurations
Same grid as SNN microcap task: Small/Medium/Large/Deep/Readout variants
Sequence lengths T ∈ [10, 20, 40] on daily data (2-8 weeks of lookback)

### Evaluation
- DM tests against quant floor (OU-based strategy, ML-enhanced strategy)
- Jump detection accuracy: precision/recall on known jump events
- Reversion timing: MAE on predicted days-to-reversion vs actual
- Trading metrics: Sharpe, drawdown, win rate
- Per-pair analysis: does SNN advantage correlate with jump frequency?

## Acceptance Criteria
- [ ] Spread-native encoding implemented
- [ ] All neuron models × architectures tested on cointegrated pairs
- [ ] Jump detection accuracy analysis
- [ ] DM tests against quant floor and LSTM baselines
- [ ] Trading strategy backtest with SNN signals
- [ ] Per-pair diagnostic
- [ ] Results exported + summary report

## Notes
- The biological analogy (homeostasis detection) is strong here — lean into it
- Adaptive LIF is the theoretically motivated choice for jump/no-jump classification
- Daily data means fewer samples — may need to pool across pairs for training
- Jump events are rare — class imbalance is real, use appropriate handling
