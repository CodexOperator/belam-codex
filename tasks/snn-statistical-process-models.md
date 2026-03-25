---
primitive: task
status: open
priority: critical
created: 2026-03-25
owner: belam
depends_on: [quant-statistical-process-models]
upstream: []
downstream: []
tags: [snn, garch, hawkes, poisson, process-models, temporal]
---

# SNN Statistical Process Models

## Research Question
Can SNNs learn the temporal dynamics encoded by statistical process models (GARCH, Hawkes, OU, Poisson) directly from raw data — or does feeding process-derived features into an SNN create a synergy that neither approach achieves alone?

## Scope
SNN and temporal neural models trained on both raw data and process-model-derived features. Two core comparisons:
1. **SNN on raw data vs SNN on process features** — does the mathematical preprocessing help?
2. **SNN on process features vs ML on process features** — does spiking add anything on top of good features?

## Design

### Experiment Grid

| Input Type | Model | What It Tests |
|------------|-------|---------------|
| V1 raw features | SNN | V1 baseline replication |
| GARCH residuals + conditional vol | SNN | Does volatility adjustment help SNN? |
| Fractionally differentiated features (optimal d) | SNN | Does preserved memory help SNN? |
| Hawkes intensity + jump indicators | SNN | Can SNN amplify self-exciting dynamics? |
| Full process-aware feature set | SNN | Kitchen sink — does everything combined help? |
| Same inputs × same grid | LSTM/GRU | Matched baselines |

### Unique SNN Investigations

**GARCH-SNN hybrid:** 
- Use GARCH conditional volatility as a **time-varying threshold** for the SNN's LIF neurons
- When vol is high → lower spike threshold → more sensitive to small moves
- When vol is low → higher threshold → filter noise
- This is biologically motivated: sensory neurons adapt thresholds based on ambient noise level

**Hawkes-SNN coupling:**
- Feed Hawkes λ(t) directly as a modulatory input (not a spike input)
- λ(t) scales the synaptic weights: high intensity → amplified response
- Tests whether the SNN can learn to "pay more attention" during self-exciting cascades

**Hurst-conditioned routing:**
- Rolling Hurst exponent determines which SNN sub-network processes the input
- H > 0.55 → "momentum SNN" (trained on trending data)
- H < 0.45 → "reversion SNN" (trained on mean-reverting data)
- 0.45 < H < 0.55 → "uncertain" → abstain or reduce position
- Mixture of experts with biologically-motivated routing

### Neuron Models
Focus on Adaptive LIF (threshold modulation is central to this module) and Synaptic (dual time constants match GARCH's dual persistence). Full comparison with Leaky, Alpha, RLeaky.

### Evaluation
- DM tests: SNN(process features) vs SNN(raw) vs ML(process features) vs ML(raw)
- Ablation: which process feature set contributes most to SNN improvement?
- GARCH-threshold adaptation: does dynamic thresholding beat fixed thresholds?
- Hurst routing accuracy: does the regime detector correctly identify trending vs reverting periods?
- All standard metrics + DSR + PBO

## Acceptance Criteria
- [ ] Full experiment grid (5 input types × 6+ neuron models × 3 architectures)
- [ ] GARCH-SNN hybrid with adaptive thresholds implemented
- [ ] Hawkes-SNN coupling implemented
- [ ] Hurst-conditioned routing implemented
- [ ] DM tests for all key comparisons
- [ ] Ablation study on process feature contributions
- [ ] Results exported + summary report

## Notes
- This is the most theoretically ambitious module — may need simplification during execution
- The GARCH-threshold idea is novel and worth a paper if it works
- Hurst routing is a mixture-of-experts design — keep the routing simple (no learnable gating initially)
- Process features need to be strictly causal — no future information in GARCH/Hawkes estimates
- Start with GJR-GARCH residuals + Hurst as the minimum viable process feature set
