---
primitive: task
status: in_pipeline
priority: high
created: 2026-03-23
owner: belam
depends_on: [build-equilibrium-snn]
upstream: []
downstream: []
tags: [snn, limbic, reward, equilibrium, research]
pipeline: limbic-reward-snn-bio-inspired-reward-neurons-for-equilibrium-network
---

# Limbic Reward SNN: Bio-Inspired Reward Neurons for Equilibrium Network

## Context

The equilibrium SNN (build-equilibrium-snn, archived) validated that:
- State persistence works (+1.83pp over reset-per-candle)
- Phasic (change) signals dominate tonic (level) signals
- Magnitude output mode produces better Sharpe (+1.09) than direction mode (-1.09)
- Output neurons are universally dead (spike rate 0.0) — the network cannot generate confident signals
- All models barely beat random (51.52% mean) — operating in a signal-starved regime

The strategic verdict was: the right architecture exists but needs better learning dynamics, not more architectural tweaks.

## Core Idea: Limbic Reward Neurons

Add a biologically-inspired limbic system to the equilibrium SNN. Instead of optimizing a traditional loss function (minimize MSE, maximize accuracy), the network is driven by **reward neurons that fire when predictions are correct**.

### Approach 1: Virtual Energy Economy
- Each neuron spike costs energy (metabolic cost)
- Correct predictions trigger limbic reward neurons that **replenish energy significantly**
- The cost function becomes: maximize limbic neuron firing rate (= maximize energy)
- Network naturally learns to: (a) be selective about firing (energy conservation), (b) fire confidently when signal is strong (energy payoff)
- This could fix the dead output neuron problem — neurons WANT to fire when they can earn energy back

### Approach 2: Profitability as Reward Signal
- Use net uplift or Sharpe ratio as a **secondary cost function**
- Add a secondary network that searches through position sizes and other profitability variables to optimize these values
- Could use these profitability metrics as the limbic reward signal itself
- The primary SNN predicts direction/magnitude, the secondary network optimizes HOW to act on those predictions
- Combines signal quality (primary) with execution quality (secondary)

### Approach 3: Hybrid — Profitability Rewards Inside Primary Network
- Integrate the position sizing / profitability optimization directly into the primary SNN
- Reward neurons fire proportional to realized PnL of the prediction
- The network simultaneously learns WHAT to predict and HOW to profit from it
- Most ambitious but closest to how biological reward systems actually work

## Architectural Sketch

```
[Input Features] → [Equilibrium SNN (tonic + phasic)]
                          ↓
                    [Output Neurons] → prediction
                          ↓
              [Limbic Reward Layer] ← actual outcome
                    ↓           ↓
              [Energy Pool]  [Reward Signal]
                    ↓           ↓
              [Modulate all neuron thresholds + learning rates]
```

## Key Questions for Architect
1. How does the energy budget interact with backprop? Is this differentiable or does it need RL-style policy gradient?
2. Should the limbic layer be spiking neurons too, or continuous-valued reward units?
3. Can we use the equilibrium SNN as-is (EQ-04 config: small-96, T=1) as the frozen backbone and only train the limbic layer first?
4. For Approach 2: what profitability variables should the secondary network optimize? (position size, holding period, entry threshold, stop-loss level?)
5. How does this relate to the validate-scheme-b finding that turnover is the Sharpe killer? Can limbic rewards penalize excessive position changes?

## References
- Equilibrium SNN report: `machinelearning/snn_applied_finance/notebooks/local_results/build-equilibrium-snn/build-equilibrium-snn_analysis_report.md`
- Validate-scheme-b report: `machinelearning/snn_applied_finance/notebooks/local_results/validate-scheme-b/validate-scheme-b_analysis_report.md`
- Archived pipeline: build-equilibrium-snn (phase2_complete)
- LFN Design Document: project knowledge (reward system architecture)
