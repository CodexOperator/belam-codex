---
primitive: project
status: active
priority: high
created: 2026-03-27
owner: belam
tags: [snn, research, neuron-architecture, energy-model, topology, frequency-matching]
related_projects: [snn-applied-finance, snn-standard-model]
---

# SNN Energy-Topology Research

Foundational research into a novel spiking neural network architecture featuring:
- **Energy-aware neurons** — spike emission and reception have energy costs; correct frequency matching earns energy
- **Pull-only connectivity** — every connection is receiver-initiated; neurons fire into the void, others choose to subscribe
- **Self-organizing topology** — processing cluster neurons form/break connections based on energy economics
- **Frequency band quantization** — discrete attractor states for output firing rates
- **Layered connection rules** — input (broadcast-only), processing (self-organizing), output (active readers)

## Core Architecture

### Layer Rules

| Layer | Can Connect FROM | Can Connect TO | Fires | Notes |
|-------|-----------------|---------------|-------|-------|
| Input | — (broadcast only) | — | Yes | Sensors. Fire spike trains from data. No outgoing connections. |
| Processing | Input, Processing | — (pull-only, no push) | Yes | Self-organizing core. Subscribe to inputs and each other. Cannot connect to output. |
| Output | Processing (Variant A) / Processing + Input (Variant B) | — | Yes (prediction) | Actively pulls from cluster. Feature selection via subscription. |

All connections are **pull-only** — the receiving neuron decides whom to listen to. No neuron controls where its output goes.

### Energy Model

| Action | Energy Cost | Notes |
|--------|------------|-------|
| Emit spike | High | Most expensive action — broadcasting costs energy |
| Receive spike | Low | Cheaper than sending — listening is efficient |
| Form new connection | Medium | Investment — must pay to subscribe |
| Maintain connection | Low (ongoing) | Drain per batch — unused connections decay naturally |
| Break connection | Free | Just stop spending — natural atrophy |
| Correct frequency match | **Earns energy** | Closer match to target = more energy earned |

**Net energy is the meta-objective.** Neurons that find useful patterns earn energy, enabling them to form more connections and find more patterns. Neurons that don't contribute can't afford connections and naturally die off.

### Training Dynamics

- **Per-sample:** Weights adjust dynamically (fine-tuning within batch)
- **Per-batch:** Connection topology changes (structural learning — subscribe/unsubscribe decisions)
- **Frequency matching:** Output neurons have target frequency bands; the closer their firing rate matches the correct band for the input, the more energy they earn
- **Weight clamps:** 0.1–10 range. No connection goes silent; no connection dominates.
- **Connection limits:** Max K connections per neuron (configurable, important for larger networks)

### Key Hypotheses

1. Energy pressure creates natural sparsity — more efficient than pruning
2. Pull-only connectivity leads to emergent feature hierarchy without explicit layer design
3. Self-organizing topology adapts to regime changes (topology IS a signal)
4. Frequency band quantization produces interpretable, discrete outputs
5. Micro-network ensembles (each on one indicator) outperform monolithic networks
6. Multi-horizon prediction benefits from temporal spike dynamics more than single-step

## Relationship to Other Projects

- **snn-standard-model** (COMPLETE): Baseline benchmarking of standard neuron models. This project builds custom neurons beyond those baselines.
- **snn-applied-finance**: Earlier SNN-on-crypto attempts. Lessons: next-candle prediction is noise; multi-horizon and binary classification work better.
- **microcap-swing-signal-extraction** (COMPLETE): Provides the data pipeline, features, and labels infrastructure. This project uses that data.

## Data Source

Uses 1-minute candle data from microcap swing data pipeline, resampled to 15m/1h/4h/daily as needed. Tokens: BONK, WIF, TRUMP, PENGU, FARTCOIN, BTC, ETH, SOL + DEX tokens.

## Implementation

Pure PyTorch — build from scratch. No snnTorch (too rigid for custom energy/topology dynamics). Keep neuron implementation clean and modular so each component (energy, frequency matching, topology) can be tested independently.
