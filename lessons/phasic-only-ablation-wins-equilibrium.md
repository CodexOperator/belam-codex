---
primitive: lesson
date: 2026-03-19
source: build-equilibrium-snn pipeline — 27 experiments, 81 runs, ablation studies
confidence: high
priority: high
tags: [snn, architecture, ablation, equilibrium, phasic]
promotion_status: exploratory
doctrine_richness: 10
contradicts: []
---

# Phasic-Only Ablation Wins in Equilibrium SNN

## The Finding

In the build-equilibrium-snn pipeline (27 experiments across 3 folds), the **phasic-only ablation (EQ-ABL-02)** achieved the highest accuracy at **52.59%** — beating all primary experiments and all baselines. This was a small-96 scale ablation variant with persistent state.

## Why This Matters

The equilibrium SNN architecture separates tonic (baseline) and phasic (change-responsive) pathways. Ablating the tonic pathway and keeping only phasic processing produced *better* results, suggesting:

1. **Phasic (change-detection) processing carries the primary signal** for financial time series at 4h resolution
2. **Tonic (absolute state) processing may add noise** or interfere with the change-detection pathway
3. This aligns with delta encoding's biological premise — neurons that detect change are more informative than neurons tracking absolute state

## Scale Analysis

| Scale | Mean Acc | N |
|-------|---------|---|
| small-96 | 0.5199 | 3 |
| micro-50 | 0.5161 | 3 |
| medium-192 | 0.5156 | 4 |
| nano-15 | 0.5146 | 2 |

Small-96 is the sweet spot — enough capacity without overfitting.

## Statistical Significance

SNN experiments significantly outperform baselines (t=2.208, p=0.0397). This is the first pipeline to demonstrate statistical significance of SNN over non-SNN baselines.

## Implication

The equilibrium SNN should be re-explored with a phasic-dominant architecture: strong phasic pathway, weak/optional tonic pathway. Combine with Scheme B regression output for the confidence-weighted abstention mechanism.
